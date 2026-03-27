import json
import uuid
from typing import List

import numpy as np
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, message_to_dict
from sqlalchemy import or_

from util.db_models import ChatMessage, SessionLocal
from util.embeddings_models import get_embeddings
from util.redis_client import (
    append_history_message,
    cache_history_messages,
    get_cached_history_messages,
)
from util.time_utils import format_datetime, now_local


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


class DbChatMessageHistory(BaseChatMessageHistory):
    def __init__(
        self,
        session_id: str,
        collection_name: str = "history",
        persist_directory: str = "./chroma_db",
    ):
        self.session_id = session_id
        self.collection_name = collection_name
        self.persist_directory = persist_directory

    def _serialize_message_record(self, msg_id: str, timestamp, message_dict: dict) -> dict:
        return {
            "id": msg_id,
            "content": message_dict,
            "message_type": message_dict["type"],
            "timestamp": format_datetime(timestamp),
        }

    def _records_to_messages(self, records: list[dict]) -> List[BaseMessage]:
        message_dicts = []
        for record in records:
            msg_dict = record["content"]
            msg_dict["metadata"] = {
                "timestamp": record["timestamp"],
                "type": record["message_type"],
                "id": record["id"],
            }
            message_dicts.append(msg_dict)
        return messages_from_dict(message_dicts)

    @property
    def messages(self) -> List[BaseMessage]:
        cached_records = get_cached_history_messages(self.session_id)
        if cached_records:
            return self._records_to_messages(cached_records)

        db = SessionLocal()
        try:
            results = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == self.session_id)
                .order_by(ChatMessage.timestamp)
                .all()
            )

            if not results:
                return []

            records = []
            for msg in results:
                records.append(
                    {
                        "id": msg.id,
                        "content": json.loads(msg.content),
                        "message_type": msg.message_type,
                        "timestamp": format_datetime(msg.timestamp),
                    }
                )

            cache_history_messages(self.session_id, records)
            return self._records_to_messages(records)
        finally:
            db.close()

    def add_message(self, message: BaseMessage) -> None:
        db = SessionLocal()
        try:
            msg_dict = message_to_dict(message)
            doc_content = json.dumps(msg_dict, ensure_ascii=False)
            timestamp = now_local()
            message_id = str(uuid.uuid4())

            embeddings = get_embeddings()
            embedding_vector = embeddings.embed_query(doc_content)
            embedding_str = json.dumps(embedding_vector)

            metadata = {
                "session_id": self.session_id,
                "timestamp": format_datetime(timestamp),
                "type": msg_dict["type"],
            }

            chat_message = ChatMessage(
                id=message_id,
                session_id=self.session_id,
                message_type=msg_dict["type"],
                content=doc_content,
                embedding=embedding_str,
                timestamp=timestamp,
                additional_metadata=json.dumps(metadata, ensure_ascii=False),
            )

            db.add(chat_message)
            db.commit()

            append_history_message(
                self.session_id,
                self._serialize_message_record(message_id, timestamp, msg_dict),
            )
        except Exception as exc:
            db.rollback()
            raise exc
        finally:
            db.close()

    def add_system_message(self, content: str, metadata: dict | None = None) -> None:
        db = SessionLocal()
        try:
            timestamp = now_local()
            message_id = str(uuid.uuid4())
            payload = {
                "type": "system",
                "data": {
                    "content": content,
                },
            }

            chat_message = ChatMessage(
                id=message_id,
                session_id=self.session_id,
                message_type="system",
                content=json.dumps(payload, ensure_ascii=False),
                embedding=None,
                timestamp=timestamp,
                additional_metadata=json.dumps(metadata or {}, ensure_ascii=False),
            )

            db.add(chat_message)
            db.commit()

            append_history_message(
                self.session_id,
                self._serialize_message_record(message_id, timestamp, payload),
            )
        except Exception as exc:
            db.rollback()
            raise exc
        finally:
            db.close()

    def clear(self) -> None:
        db = SessionLocal()
        try:
            db.query(ChatMessage).filter(ChatMessage.session_id == self.session_id).delete()
            db.commit()
            cache_history_messages(self.session_id, [])
        except Exception as exc:
            db.rollback()
            raise exc
        finally:
            db.close()

    def search_similar(self, query: str, k: int = 5) -> List[BaseMessage]:
        db = SessionLocal()
        try:
            embeddings = get_embeddings()
            query_vector = np.array(embeddings.embed_query(query), dtype=float)

            results = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == self.session_id)
                .filter(or_(ChatMessage.message_type == "human", ChatMessage.message_type == "ai"))
                .all()
            )
            if not results:
                return []

            similarities = []
            skipped_dimension_mismatches = 0
            for msg in results:
                stored_embedding = _load_embedding_array(msg.embedding)
                if stored_embedding is None:
                    continue
                if stored_embedding.shape != query_vector.shape:
                    skipped_dimension_mismatches += 1
                    continue
                similarity = np.dot(query_vector, stored_embedding)
                similarities.append((similarity, msg))

            if not similarities and skipped_dimension_mismatches:
                return []

            similarities.sort(key=lambda item: item[0], reverse=True)
            top_k = similarities[:k]

            messages = []
            for _, msg in top_k:
                msg_dict = json.loads(msg.content)
                messages.append(messages_from_dict([msg_dict])[0])
            return messages
        finally:
            db.close()

    def search_early_history(self, query: str, k: int = 5, recent_turns_to_skip: int = 5) -> List[BaseMessage]:
        db = SessionLocal()
        try:
            embeddings = get_embeddings()
            query_vector = np.array(embeddings.embed_query(query), dtype=float)

            results = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == self.session_id)
                .filter(or_(ChatMessage.message_type == "human", ChatMessage.message_type == "ai"))
                .order_by(ChatMessage.timestamp)
                .all()
            )
            if not results:
                return []

            skip_messages = recent_turns_to_skip * 2
            candidate_results = results[:-skip_messages] if len(results) > skip_messages else []
            if not candidate_results:
                return []

            similarities = []
            skipped_dimension_mismatches = 0
            for msg in candidate_results:
                stored_embedding = _load_embedding_array(msg.embedding)
                if stored_embedding is None:
                    continue
                if stored_embedding.shape != query_vector.shape:
                    skipped_dimension_mismatches += 1
                    continue
                similarity = np.dot(query_vector, stored_embedding)
                similarities.append((similarity, msg))

            if not similarities and skipped_dimension_mismatches:
                return []

            similarities.sort(key=lambda item: item[0], reverse=True)
            top_k = similarities[:k]

            messages = []
            for _, msg in top_k:
                msg_dict = json.loads(msg.content)
                messages.append(messages_from_dict([msg_dict])[0])
            return messages
        finally:
            db.close()
