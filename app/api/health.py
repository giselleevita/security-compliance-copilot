from fastapi import APIRouter, HTTPException

from app.core.dependencies import get_health_status, get_readiness_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return get_health_status()


@router.get("/ready")
def ready() -> dict:
    status = get_readiness_status()
    if not status["ready"]:
        raise HTTPException(status_code=503, detail=status)
    return status
