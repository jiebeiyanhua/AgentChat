import logging
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from util.config import get_str
from util.time_utils import now_local

POSTGRES_HOST = get_str("postgres.host", "localhost")
POSTGRES_PORT = get_str("postgres.port", "5432")
POSTGRES_DB = get_str("postgres.db")
POSTGRES_USER = get_str("postgres.user")
POSTGRES_PASSWORD = get_str("postgres.password")

if not all([POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]):
    raise ValueError("Please configure complete PostgreSQL settings.")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
logger = logging.getLogger(__name__)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True)
    session_id = Column(String, index=True, nullable=False)
    message_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=now_local)
    additional_metadata = Column(Text, nullable=True)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String, primary_key=True)
    source_key = Column(String, index=True, nullable=False)
    source_name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    content_hash = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=now_local, nullable=False)


class KnowledgeDefinition(Base):
    __tablename__ = "knowledge_definitions"

    id = Column(String, primary_key=True)
    source_key = Column(String, unique=True, index=True, nullable=False)
    source_name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    content_hash = Column(String, nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=now_local, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
