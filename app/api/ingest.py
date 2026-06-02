from fastapi import APIRouter, Header, HTTPException

from app.core.config import get_settings
from app.core.dependencies import get_ingestion_pipeline

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
def ingest(x_ingest_token: str | None = Header(default=None)) -> dict:
    settings = get_settings()
    if not settings.ingest_api_key or x_ingest_token != settings.ingest_api_key:
        raise HTTPException(status_code=403, detail="Ingestion endpoint is protected.")
    pipeline = get_ingestion_pipeline()
    try:
        result = pipeline.run()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "ingested_documents": result.documents_processed,
        "stored_chunks": result.chunks_stored,
    }
