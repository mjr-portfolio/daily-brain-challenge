from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.services.queue_manager import replenish_queue

logger = logging.getLogger(__name__)
settings = get_settings()


async def _boot_replenish() -> None:
    try:
        async with AsyncSessionLocal() as session:
            summary = await replenish_queue(session)
        logger.info("Boot queue replenish complete: %s", summary)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Boot queue replenish failed")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    task: asyncio.Task[None] | None = None
    if settings.GEMINI_API_KEY:
        task = asyncio.create_task(_boot_replenish())
        logger.info("Started background queue replenish on boot")
    else:
        logger.info("Skipping boot queue replenish: GEMINI_API_KEY is not set")

    try:
        yield
    finally:
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
