from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import chat, health
from app.config import get_settings, validate_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_settings(get_settings())
    yield


app = FastAPI(title="AI Purchasing Agent", lifespan=lifespan)
app.include_router(health.router)
app.include_router(chat.router, prefix="/api")
