import os

from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from util.time_utils import now_local

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

if not all([POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]):
    raise ValueError("Please configure complete PostgreSQL settings.")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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
    print("Database initialized.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
