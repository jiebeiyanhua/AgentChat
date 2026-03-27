import os
import threading
import logging

import numpy as np
import requests
from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

MODEL = os.getenv("MODEL")
DEVICE = os.getenv("DEVICE")
NORMALIZE_EMBEDDINGS = os.getenv("NORMALIZE_EMBEDDINGS")
EMBEDDING_PROVIDER = (os.getenv("EMBEDDING_PROVIDER") or "huggingface").strip().lower()
OLLAMA_BASE_URL = (os.getenv("OLLAMA_BASE_URL") or "http://ollama:11434").rstrip("/")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

if not NORMALIZE_EMBEDDINGS:
    raise ValueError("Please configure NORMALIZE_EMBEDDINGS in .env")

if EMBEDDING_PROVIDER == "huggingface" and (not MODEL or not DEVICE):
    raise ValueError("Please configure MODEL, DEVICE, and NORMALIZE_EMBEDDINGS in .env")

_embeddings = None
_lock = threading.Lock()
_initialized = False
logger = logging.getLogger(__name__)


def _should_normalize() -> bool:
    return NORMALIZE_EMBEDDINGS.lower() == "true"


def _normalize_vector(vector: list[float]) -> list[float]:
    if not _should_normalize():
        return vector
    array = np.array(vector, dtype=float)
    norm = np.linalg.norm(array)
    if norm == 0:
        return array.tolist()
    return (array / norm).tolist()


def _normalize_vectors(vectors: list[list[float]]) -> list[list[float]]:
    return [_normalize_vector(vector) for vector in vectors]


def ensure_model_downloaded():
    logger.info("Checking embedding model cache: %s", MODEL)
    snapshot_download(
        repo_id=MODEL,
        cache_dir="./models",
    )


def get_model_path():
    cache_dir = "./models"
    if not os.path.exists(cache_dir):
        logger.warning("Model cache directory does not exist: %s", cache_dir)
        return MODEL

    model_parts = MODEL.split("/")
    if len(model_parts) != 2:
        logger.warning("Unexpected model name format: %s", MODEL)
        return MODEL

    org, model_name = model_parts
    expected_dir = f"models--{org}--{model_name}"
    model_cache_path = os.path.join(cache_dir, expected_dir)

    if os.path.exists(model_cache_path):
        snapshots_dir = os.path.join(model_cache_path, "snapshots")
        if os.path.exists(snapshots_dir):
            snapshot_dirs = [
                directory
                for directory in os.listdir(snapshots_dir)
                if os.path.isdir(os.path.join(snapshots_dir, directory))
            ]
            if snapshot_dirs:
                actual_model_path = os.path.join(snapshots_dir, snapshot_dirs[0])
                logger.info("Using cached embedding snapshot: %s", actual_model_path)
                return actual_model_path

    logger.info("Searching model files in cache directory...")
    for root, _, files in os.walk(cache_dir):
        if any(
            filename in files
            for filename in [
                "config.json",
                "pytorch_model.bin",
                "model.safetensors",
                "sentence_bert_config.json",
            ]
        ):
            logger.info("Using discovered model directory: %s", root)
            return root

    logger.warning("Local model cache not found, fallback to remote model id: %s", MODEL)
    return MODEL


def ensure_ollama_model(model_name: str):
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/pull",
        json={"model": model_name, "stream": False},
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()


def _init_embeddings():
    global _embeddings, _initialized
    if _initialized:
        return

    with _lock:
        if _initialized:
            return

        print(f"[Thread {threading.current_thread().ident}] Initializing embedding model...")

        try:
            if EMBEDDING_PROVIDER == "ollama":
                model_name = OLLAMA_EMBED_MODEL or MODEL
                if not model_name:
                    raise ValueError("Please configure OLLAMA_EMBED_MODEL or MODEL when EMBEDDING_PROVIDER=ollama.")

                ensure_ollama_model(model_name)
                _embeddings = OllamaEmbeddings(
                    model=model_name,
                    base_url=OLLAMA_BASE_URL,
                    timeout=OLLAMA_TIMEOUT,
                )
            else:
                ensure_model_downloaded()
                model_path = get_model_path()

                from sentence_transformers import SentenceTransformer

                if os.path.exists(model_path) and os.path.isdir(model_path):
                    logger.info(f"Loading embedding model from local path: {model_path}")
                    st_model = SentenceTransformer(model_path, device=DEVICE)
                else:
                    logger.info(f"Loading embedding model from HuggingFace: {MODEL}")
                    st_model = SentenceTransformer(MODEL, device=DEVICE)

                _embeddings = SentenceTransformerEmbeddings(
                    st_model,
                    normalize_embeddings=_should_normalize(),
                )

            test_result = _embeddings.embed_query("test")
            logger.info(
                f"[Thread {threading.current_thread().ident}] "
                f"Embedding model ready, vector dimension: {len(test_result)}"
            )
            _initialized = True
        except Exception as exc:
            logger.exception(
                "[Thread %s] Failed to initialize embedding model: %s",
                threading.current_thread().ident,
                exc,
            )
            import traceback

            traceback.print_exc()
            raise


def init_embeddings():
    _init_embeddings()
    return _embeddings


def get_embeddings():
    global _embeddings
    if not _initialized:
        _init_embeddings()

    if _embeddings is None:
        raise RuntimeError("Embedding model was not initialized correctly")

    return _embeddings


class SentenceTransformerEmbeddings:
    def __init__(self, model, normalize_embeddings=True):
        self.model = model
        self.normalize_embeddings = normalize_embeddings

    def embed_documents(self, texts):
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text):
        embedding = self.model.encode(
            text,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
        )
        return embedding.tolist()


class OllamaEmbeddings:
    def __init__(self, model: str, base_url: str, timeout: int = 120):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post_embed(self, payload: dict) -> dict:
        response = requests.post(
            f"{self.base_url}/api/embed",
            json=payload,
            timeout=self.timeout,
        )
        if response.ok:
            return response.json()

        fallback_response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": payload["input"] if isinstance(payload["input"], str) else payload["input"][0]},
            timeout=self.timeout,
        )
        fallback_response.raise_for_status()
        return fallback_response.json()

    def embed_documents(self, texts):
        if not texts:
            return []
        data = self._post_embed({"model": self.model, "input": texts})
        if "embeddings" in data:
            return _normalize_vectors(data["embeddings"])
        if "embedding" in data:
            return [_normalize_vector(data["embedding"])]
        raise ValueError("Unexpected Ollama embedding response")

    def embed_query(self, text):
        data = self._post_embed({"model": self.model, "input": text})
        if "embeddings" in data:
            return _normalize_vector(data["embeddings"][0])
        if "embedding" in data:
            return _normalize_vector(data["embedding"])
        raise ValueError("Unexpected Ollama embedding response")
