import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import func

from util.db_models import KnowledgeChunk, SessionLocal
from util.embeddings_models import get_embeddings

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50

DEFINITION_SOURCES = {
    "SOUL": Path("definition/SOUL.md"),
    "USER": Path("definition/USER.md"),
}


@dataclass
class KnowledgeSourceSummary:
    source_key: str
    source_name: str
    source_type: str
    file_path: str | None
    chunk_count: int
    updated_at: str | None


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        separators=["\n## ", "\n# "],
        length_function=len,
    )
    chunks = [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]
    if chunks:
        return chunks
    stripped_text = text.strip()
    return [stripped_text] if stripped_text else []


def _replace_source_chunks(
    source_key: str,
    source_name: str,
    source_type: str,
    text: str,
    *,
    file_path: str | None = None,
) -> dict:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Knowledge base content cannot be empty.")

    content_hash = _hash_text(normalized_text)
    chunks = _split_text(normalized_text)
    embeddings = get_embeddings().embed_documents(chunks)
    updated_at = datetime.now(timezone.utc)

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
        db.commit()
        return {
            "source_key": source_key,
            "source_name": source_name,
            "source_type": source_type,
            "file_path": file_path,
            "chunk_count": len(chunks),
            "content_hash": content_hash,
            "updated_at": updated_at.isoformat(),
            "updated": True,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _get_source_hash(source_key: str) -> str | None:
    db = SessionLocal()
    try:
        row = (
            db.query(KnowledgeChunk.content_hash)
            .filter(KnowledgeChunk.source_key == source_key)
            .first()
        )
        return row[0] if row else None
    finally:
        db.close()


def sync_text_source(
    source_key: str,
    source_name: str,
    source_type: str,
    text: str,
    *,
    file_path: str | None = None,
) -> dict:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Knowledge base content cannot be empty.")

    incoming_hash = _hash_text(normalized_text)
    existing_hash = _get_source_hash(source_key)
    if existing_hash == incoming_hash:
        return {
            "source_key": source_key,
            "source_name": source_name,
            "source_type": source_type,
            "file_path": file_path,
            "content_hash": incoming_hash,
            "updated": False,
        }

    return _replace_source_chunks(
        source_key,
        source_name,
        source_type,
        normalized_text,
        file_path=file_path,
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
    )


def ensure_default_definition_sources() -> list[dict]:
    results = []
    for definition_name, file_path in DEFINITION_SOURCES.items():
        result = sync_definition_source(definition_name, file_path)
        if result is not None:
            results.append(result)
    return results


def store_uploaded_knowledge(filename: str, content: bytes) -> dict:
    text = content.decode("utf-8", errors="ignore").strip()
    if not text:
        raise ValueError("Uploaded file is empty or cannot be decoded as UTF-8 text.")

    return sync_text_source(
        source_key=f"upload:{filename}",
        source_name=filename,
        source_type="upload",
        text=text,
        file_path=filename,
    )


def search_knowledge_base(query: str, k: int = 5) -> list[dict]:
    query_text = query.strip()
    if not query_text:
        return []

    db = SessionLocal()
    try:
        rows = db.query(KnowledgeChunk).all()
        if not rows:
            return []

        query_vector = np.array(get_embeddings().embed_query(query_text))
        scored_rows = []
        for row in rows:
            stored_embedding = np.array(json.loads(row.embedding))
            similarity = float(np.dot(query_vector, stored_embedding))
            scored_rows.append((similarity, row))

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


def list_knowledge_sources() -> list[KnowledgeSourceSummary]:
    db = SessionLocal()
    try:
        rows = (
            db.query(
                KnowledgeChunk.source_key,
                KnowledgeChunk.source_name,
                KnowledgeChunk.source_type,
                KnowledgeChunk.file_path,
                func.count(KnowledgeChunk.id),
                func.max(KnowledgeChunk.updated_at),
            )
            .group_by(
                KnowledgeChunk.source_key,
                KnowledgeChunk.source_name,
                KnowledgeChunk.source_type,
                KnowledgeChunk.file_path,
            )
            .order_by(func.max(KnowledgeChunk.updated_at).desc())
            .all()
        )

        return [
            KnowledgeSourceSummary(
                source_key=row[0],
                source_name=row[1],
                source_type=row[2],
                file_path=row[3],
                chunk_count=row[4],
                updated_at=row[5].isoformat() if row[5] else None,
            )
            for row in rows
        ]
    finally:
        db.close()
