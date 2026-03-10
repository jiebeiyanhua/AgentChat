import os
import uuid
import json
import numpy as np
from datetime import datetime, timezone
from typing import List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, message_to_dict

from util.db_models import ChatMessage, SessionLocal, init_db
from util.embeddings_models import get_embeddings

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

        init_db()

    @property
    def messages(self) -> List[BaseMessage]:
        db = SessionLocal()
        try:
            results = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id
            ).order_by(ChatMessage.timestamp).all()
            
            if not results:
                return []
            
            message_dicts = []
            for msg in results:
                msg_dict = json.loads(msg.content)
                msg_dict["metadata"] = {
                    "timestamp": msg.timestamp.isoformat(),
                    "type": msg.message_type,
                    "id": msg.id
                }
                message_dicts.append(msg_dict)
            
            return messages_from_dict(message_dicts)
        finally:
            db.close()

    def add_message(self, message: BaseMessage) -> None:
        db = SessionLocal()
        try:
            msg_dict = message_to_dict(message)
            doc_content = json.dumps(msg_dict, ensure_ascii=False)
            
            embeddings = get_embeddings()
            embedding_vector = embeddings.embed_query(doc_content)
            embedding_str = json.dumps(embedding_vector)
            
            metadata = {
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": msg_dict["type"],
            }
            
            chat_message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                message_type=msg_dict["type"],
                content=doc_content,
                embedding=embedding_str,
                timestamp=datetime.now(timezone.utc),
                additional_metadata=json.dumps(metadata)
            )
            
            db.add(chat_message)
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def clear(self) -> None:
        db = SessionLocal()
        try:
            db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def search_similar(self, query: str, k: int = 5) -> List[BaseMessage]:
        db = SessionLocal()
        try:
            embeddings = get_embeddings()
            query_embedding = embeddings.embed_query(query)
            query_vector = np.array(query_embedding)
            
            results = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id
            ).all()
            
            if not results:
                return []
            
            similarities = []
            for msg in results:
                if msg.embedding:
                    stored_embedding = np.array(json.loads(msg.embedding))
                    similarity = np.dot(query_vector, stored_embedding)
                    similarities.append((similarity, msg))
            
            similarities.sort(key=lambda x: x[0], reverse=True)
            top_k = similarities[:k]
            
            messages = []
            for _, msg in top_k:
                msg_dict = json.loads(msg.content)
                messages.append(messages_from_dict([msg_dict])[0])
            
            return messages
        finally:
            db.close()
