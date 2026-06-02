import logging
from typing import Any

from app.models.source import SourceChunk

logger = logging.getLogger(__name__)


TRUSTED_FRAMEWORK_BONUSES = {
    "NIST_AI_RMF": 0.08,
    "NIST_CSF": 0.08,
    "CISA": 0.07,
    "FTC": 0.04,
}

TRUSTED_PUBLISHER_KEYWORDS = ("nist", "cisa", "ftc", "fbi", "nsa")


class MetadataBoostingReranker:
    """Fallback scorer that is intentionally metadata-only, not semantic reranking."""

    def rerank(self, query: str, chunks: list[SourceChunk], limit: int) -> list[SourceChunk]:
        scored = [self._with_rerank_score(chunk) for chunk in chunks]
        ranked = sorted(
            scored,
            key=lambda chunk: (
                chunk.rerank_score or 0.0,
                chunk.score,
                -chunk.chunk_index,
            ),
            reverse=True,
        )
        return ranked[:limit]

    def _with_rerank_score(self, chunk: SourceChunk) -> SourceChunk:
        metadata_bonus = 0.0
        if chunk.framework in TRUSTED_FRAMEWORK_BONUSES:
            metadata_bonus += TRUSTED_FRAMEWORK_BONUSES[chunk.framework]
        if chunk.publisher and any(keyword in chunk.publisher.lower() for keyword in TRUSTED_PUBLISHER_KEYWORDS):
            metadata_bonus += 0.03
        if chunk.section and chunk.section.lower() not in {"introduction", "unknown section"}:
            metadata_bonus += 0.03
        if chunk.title and chunk.url:
            metadata_bonus += 0.02
        if chunk.source_type in {"md", "html", "pdf"}:
            metadata_bonus += 0.02

        rerank_score = round(chunk.score + metadata_bonus, 4)
        return chunk.model_copy(update={"rerank_score": rerank_score})


class CrossEncoderReranker:
    def __init__(
        self,
        model_name: str,
        model: Any | None = None,
        fallback: MetadataBoostingReranker | None = None,
    ) -> None:
        self.model_name = model_name
        self._model = model
        self.fallback = fallback or MetadataBoostingReranker()

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            logger.info("Loading cross-encoder reranker: %s", self.model_name)
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, chunks: list[SourceChunk], limit: int) -> list[SourceChunk]:
        if not chunks:
            return []
        pairs = [(query, chunk.text) for chunk in chunks]
        try:
            raw_scores = self.model.predict(pairs)
        except Exception:
            logger.exception("Cross-encoder reranking failed; using metadata boosting fallback")
            return self.fallback.rerank(query=query, chunks=chunks, limit=limit)

        scored: list[SourceChunk] = []
        for chunk, raw_score in zip(chunks, raw_scores):
            scored.append(chunk.model_copy(update={"rerank_score": round(float(raw_score), 4)}))
        return sorted(scored, key=lambda chunk: chunk.rerank_score or 0.0, reverse=True)[:limit]
