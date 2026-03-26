import os
import threading
import logging

from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

MODEL = os.getenv("MODEL")
DEVICE = os.getenv("DEVICE")
NORMALIZE_EMBEDDINGS = os.getenv("NORMALIZE_EMBEDDINGS")

if not MODEL or not DEVICE or not NORMALIZE_EMBEDDINGS:
    raise ValueError("Please configure MODEL, DEVICE, and NORMALIZE_EMBEDDINGS in .env")

_embeddings = None
_lock = threading.Lock()
_initialized = False
logger = logging.getLogger(__name__)


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


def _init_embeddings():
    global _embeddings, _initialized
    if _initialized:
        return

    with _lock:
        if _initialized:
            return

        logger.info("[Thread %s] Initializing embedding model...", threading.current_thread().ident)
        ensure_model_downloaded()
        model_path = get_model_path()

        try:
            from sentence_transformers import SentenceTransformer

            if os.path.exists(model_path) and os.path.isdir(model_path):
                logger.info("Loading embedding model from local path: %s", model_path)
                st_model = SentenceTransformer(model_path, device=DEVICE)
            else:
                logger.info("Loading embedding model from HuggingFace: %s", MODEL)
                st_model = SentenceTransformer(MODEL, device=DEVICE)

            _embeddings = SentenceTransformerEmbeddings(
                st_model,
                normalize_embeddings=NORMALIZE_EMBEDDINGS.lower() == "true",
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
