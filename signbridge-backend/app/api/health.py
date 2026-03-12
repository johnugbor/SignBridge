"""Basic health endpoints used by deployment probes."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
	return {"status": "ok"}


@router.get("/readiness", summary="Readiness probe")
async def readiness() -> dict:
	return {"status": "ready"}
