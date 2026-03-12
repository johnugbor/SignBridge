"""FastAPI entrypoint for SignBridge backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import health
from .api.websocket import get_websocket_router
from .config import get_settings
from .dependencies import get_logger

settings = get_settings()
logger = get_logger()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(get_websocket_router())


@app.on_event("startup")
async def startup_event() -> None:
	logger.info("SignBridge backend starting", extra={"ws": settings.websocket_route})


@app.on_event("shutdown")
async def shutdown_event() -> None:
	logger.info("SignBridge backend shutting down")
