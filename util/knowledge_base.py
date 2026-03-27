import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

from util.db_models import KnowledgeChunk, KnowledgeDefinition, SessionLocal
from util.embeddings_models import get_embeddings
from util.time_utils import format_datetime, now_local

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_DESCRIPTION_MAX_LENGTH = 180

DEFINITION_SOURCES = {
    "SOUL": Path("definition/SOUL.md"),
    "USER": Path("definition/USER.md"),
}

DEFINITION_SOURCE_DESCRIPTIONS = {
    "definition:SOUL": "Agent 的自我设定、身份认知、性格风格与行为准则。",
    "definition:USER": "关于当前用户的资料、偏好、背景信息与相处方式。",
}


def _load_embedding_array(raw_embedding: str | None) -> np.ndarray | None:
    if not raw_embedding:
        return None

    try:
        embedding = json.loads(raw_embedding)
    except (TypeError, json.JSONDecodeError):
        return None

    array = np.array(embedding, dtype=float)
    if array.ndim != 1 or array.size == 0:
        return None
    return array


@dataclass
class KnowledgeSourceSummary:
    source_key: str
    source_name: str
    source_type: str
    file_path: str | None
    description: str
    chunk_count: int
    updated_at: str | None


@dataclass
class KnowledgeDefinitionSummary:
    source_key: str
    source_name: str
    source_type: str
    file_path: str | None
    description: str
    chunk_count: int
    updated_at: str | None


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        separators=["\n## ", "\n# ", "\n\n", "\n", " "],
        length_function=len,
    )
    chunks = [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]
    if chunks:
        return chunks
    stripped_text = text.strip()
    return [stripped_text] if stripped_text else []


def _infer_description(source_key: str, source_name: str, source_type: str, text: str) -> str:
    predefined = DEFINITION_SOURCE_DESCRIPTIONS.get(source_key)
    if predefined:
        return predefined

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        if line:
            return line[:DEFAULT_DESCRIPTION_MAX_LENGTH]

    return f"{source_type} knowledge source: {source_name}"[:DEFAULT_DESCRIPTION_MAX_LENGTH]


def _normalize_description(
    description: str | None,
    *,
    source_key: str,
    source_name: str,
    source_type: str,
    text: str,
) -> str:
    normalized = (description or "").strip()
    if normalized:
        return normalized[:DEFAULT_DESCRIPTION_MAX_LENGTH]
    return _infer_description(source_key, source_name, source_type, text)


def _upsert_definition(
    db,
    *,
    source_key: str,
    source_name: str,
    source_type: str,
    file_path: str | None,
    description: str,
    content_hash: str,
    chunk_count: int,
    updated_at: datetime,
):
    definition = (
        db.query(KnowledgeDefinition)
        .filter(KnowledgeDefinition.source_key == source_key)
        .one_or_none()
    )
    if definition is None:
        definition = KnowledgeDefinition(
            id=str(uuid.uuid4()),
            source_key=source_key,
            source_name=source_name,
            source_type=source_type,
            file_path=file_path,
            description=description,
            content_hash=content_hash,
            chunk_count=chunk_count,
            updated_at=updated_at,
        )
        db.add(definition)
        return

    definition.source_name = source_name
    definition.source_type = source_type
    definition.file_path = file_path
    definition.description = description
    definition.content_hash = content_hash
    definition.chunk_count = chunk_count
    definition.updated_at = updated_at


def _replace_source_chunks(
    source_key: str,
    source_name: str,
    source_type: str,
    text: str,
    *,
    file_path: str | None = None,
    description: str | None = None,
) -> dict:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Knowledge base content cannot be empty.")

    normalized_description = _normalize_description(
        description,
        source_key=source_key,
        source_name=source_name,
        source_type=source_type,
        text=normalized_text,
    )
    content_hash = _hash_text(normalized_text)
    chunks = _split_text(normalized_text)
    embeddings = get_embeddings().embed_documents(chunks)
    updated_at = now_local()

    db = SessionLocal()
    try:
        db.query(KnowledgeChunk).filter(KnowledgeChunk.source_key == source_key).delete()
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db.add(
                KnowledgeChunk(
                    id=str(uuid.uuid4()),
                    source_key=source_key,
                    source_name=source_name,
                    source_type=source_type,
                    file_path=file_path,
                    content_hash=content_hash,
                    chunk_index=index,
                    content=chunk,
                    embedding=json.dumps(embedding),
                    updated_at=updated_at,
                )
            )

        _upsert_definition(
            db,
            source_key=source_key,
            source_name=source_name,
            source_type=source_type,
            file_path=file_path,
            description=normalized_description,
            content_hash=content_hash,
            chunk_count=len(chunks),
            updated_at=updated_at,
        )
        db.commit()
        return {
            "source_key": source_key,
            "source_name": source_name,
            "source_type": source_type,
            "file_path": file_path,
            "description": normalized_description,
            "chunk_count": len(chunks),
            "content_hash": content_hash,
            "updated_at": format_datetime(updated_at),
            "updated": True,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _get_source_definition(source_key: str) -> KnowledgeDefinition | None:
    db = SessionLocal()
    try:
        return (
            db.query(KnowledgeDefinition)
            .filter(KnowledgeDefinition.source_key == source_key)
            .one_or_none()
        )
    finally:
        db.close()


def sync_text_source(
    source_key: str,
    source_name: str,
    source_type: str,
    text: str,
    *,
    file_path: str | None = None,
    description: str | None = None,
) -> dict:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Knowledge base content cannot be empty.")

    normalized_description = _normalize_description(
        description,
        source_key=source_key,
        source_name=source_name,
        source_type=source_type,
        text=normalized_text,
    )
    incoming_hash = _hash_text(normalized_text)
    existing_definition = _get_source_definition(source_key)
    metadata_unchanged = (
        existing_definition is not None
        and existing_definition.content_hash == incoming_hash
        and existing_definition.description == normalized_description
        and existing_definition.source_name == source_name
        and existing_definition.source_type == source_type
        and existing_definition.file_path == file_path
    )
    if metadata_unchanged:
        return {
            "source_key": source_key,
            "source_name": source_name,
            "source_type": source_type,
            "file_path": file_path,
            "description": normalized_description,
            "content_hash": incoming_hash,
            "chunk_count": existing_definition.chunk_count,
            "updated_at": format_datetime(existing_definition.updated_at),
            "updated": False,
        }

    if existing_definition is not None and existing_definition.content_hash == incoming_hash:
        updated_at = now_local()
        db = SessionLocal()
        try:
            _upsert_definition(
                db,
                source_key=source_key,
                source_name=source_name,
                source_type=source_type,
                file_path=file_path,
                description=normalized_description,
                content_hash=incoming_hash,
                chunk_count=existing_definition.chunk_count,
                updated_at=updated_at,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        return {
            "source_key": source_key,
            "source_name": source_name,
            "source_type": source_type,
            "file_path": file_path,
            "description": normalized_description,
            "content_hash": incoming_hash,
            "chunk_count": existing_definition.chunk_count,
            "updated_at": format_datetime(updated_at),
            "updated": False,
        }

    return _replace_source_chunks(
        source_key,
        source_name,
        source_type,
        normalized_text,
        file_path=file_path,
        description=normalized_description,
    )


def sync_definition_source(definition_name: str, file_path: Path) -> dict | None:
    if not file_path.exists():
        return None

    return sync_text_source(
        source_key=f"definition:{definition_name}",
        source_name=definition_name,
        source_type="definition",
        text=file_path.read_text(encoding="utf-8"),
        file_path=str(file_path),
        description=DEFINITION_SOURCE_DESCRIPTIONS.get(f"definition:{definition_name}"),
    )


def ensure_default_definition_sources() -> list[dict]:
    results = []
    for definition_name, file_path in DEFINITION_SOURCES.items():
        result = sync_definition_source(definition_name, file_path)
        if result is not None:
            results.append(result)
    return results


def ensure_knowledge_definitions() -> list[dict]:
    db = SessionLocal()
    try:
        grouped_sources = db.query(KnowledgeChunk.source_key).distinct().all()
    finally:
        db.close()

    results = []
    for (source_key,) in grouped_sources:
        definition = _get_source_definition(source_key)
        if definition is not None:
            continue

        db = SessionLocal()
        try:
            chunks = (
                db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.source_key == source_key)
                .order_by(KnowledgeChunk.chunk_index.asc())
                .all()
            )
            if not chunks:
                continue
            combined_text = "\n\n".join(chunk.content for chunk in chunks)
            updated_at = max(chunk.updated_at for chunk in chunks if chunk.updated_at is not None)
            _upsert_definition(
                db,
                source_key=chunks[0].source_key,
                source_name=chunks[0].source_name,
                source_type=chunks[0].source_type,
                file_path=chunks[0].file_path,
                description=_infer_description(chunks[0].source_key, chunks[0].source_name, chunks[0].source_type, combined_text),
                content_hash=chunks[0].content_hash,
                chunk_count=len(chunks),
                updated_at=updated_at,
            )
            db.commit()
            results.append({"source_key": source_key, "backfilled": True})
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    return results


def store_uploaded_knowledge(filename: str, content: bytes, description: str | None = None) -> dict:
    text = content.decode("utf-8", errors="ignore").strip()
    if not text:
        raise ValueError("Uploaded file is empty or cannot be decoded as UTF-8 text.")

    return sync_text_source(
        source_key=f"upload:{filename}",
        source_name=filename,
        source_type="upload",
        text=text,
        file_path=filename,
        description=description,
    )


def search_knowledge_base(query: str, source_key: str, k: int = 5) -> list[dict]:
    query_text = query.strip()
    selected_source = source_key.strip()
    if not query_text or not selected_source:
        return []

    db = SessionLocal()
    try:
        rows = db.query(KnowledgeChunk).filter(KnowledgeChunk.source_key == selected_source).all()
        if not rows:
            return []

        query_vector = np.array(get_embeddings().embed_query(query_text), dtype=float)
        scored_rows = []
        skipped_dimension_mismatches = 0
        for row in rows:
            stored_embedding = _load_embedding_array(row.embedding)
            if stored_embedding is None:
                continue
            if stored_embedding.shape != query_vector.shape:
                skipped_dimension_mismatches += 1
                continue
            similarity = float(np.dot(query_vector, stored_embedding))
            scored_rows.append((similarity, row))

        if not scored_rows and skipped_dimension_mismatches:
            raise ValueError(
                "Current embedding model dimension does not match stored knowledge vectors. "
                "Please resync or re-upload the knowledge base after changing the embedding model."
            )

        scored_rows.sort(key=lambda item: item[0], reverse=True)
        results = []
        for similarity, row in scored_rows[:k]:
            results.append(
                {
                    "source_key": row.source_key,
                    "source_name": row.source_name,
                    "source_type": row.source_type,
                    "content": row.content,
                    "similarity": similarity,
                }
            )
        return results
    finally:
        db.close()


def list_knowledge_definitions() -> list[KnowledgeDefinitionSummary]:
    db = SessionLocal()
    try:
        rows = db.query(KnowledgeDefinition).order_by(KnowledgeDefinition.updated_at.desc()).all()
        return [
            KnowledgeDefinitionSummary(
                source_key=row.source_key,
                source_name=row.source_name,
                source_type=row.source_type,
                file_path=row.file_path,
                description=row.description,
                chunk_count=row.chunk_count,
                updated_at=format_datetime(row.updated_at),
            )
            for row in rows
        ]
    finally:
        db.close()


def list_knowledge_sources() -> list[KnowledgeSourceSummary]:
    return [
        KnowledgeSourceSummary(
            source_key=item.source_key,
            source_name=item.source_name,
            source_type=item.source_type,
            file_path=item.file_path,
            description=item.description,
            chunk_count=item.chunk_count,
            updated_at=item.updated_at,
        )
        for item in list_knowledge_definitions()
    ]
