from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
