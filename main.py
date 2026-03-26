from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controller.chat_controller import router as chat_router
from controller.config_controller import router as config_router
from util.db_models import init_db
from util.embeddings_models import init_embeddings
from util.knowledge_base import ensure_default_definition_sources
from util.redis_client import get_redis_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Initializing application resources.")
    init_db()
    init_embeddings()
    get_redis_client().ping()
    ensure_default_definition_sources()
    logger.info("Application resources ready.")
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)
app.include_router(config_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
