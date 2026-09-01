import json
import logging
import math
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from app.models.source import SourceChunk

logger = logging.getLogger(__name__)


class SidecarMetadataStore:
    def __init__(self, raw_dir: str | None = None) -> None:
        self.by_url: dict[str, dict] = {}
        self.by_title: dict[str, dict] = {}
        if not raw_dir:
            return

        for sidecar_path in Path(raw_dir).glob("*.metadata.json"):
            payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            url = str(payload.get("url") or "").strip()
            title = str(payload.get("title") or "").strip()
            if url:
                self.by_url[url] = payload
            if title:
                self.by_title[title] = payload

    def lookup(self, url: str, title: str) -> dict:
        if url and url in self.by_url:
            return self.by_url[url]
        if title and title in self.by_title:
            return self.by_title[title]
        return {}


class SqliteVectorStore:
    def __init__(self, persist_directory: str, collection_name: str, raw_dir: str | None = None) -> None:
        directory = Path(persist_directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.database_path = directory / f"{collection_name}.sqlite3"
        self.connection = sqlite3.connect(self.database_path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document TEXT NOT NULL,
                metadata TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
            """
        )
        self.connection.commit()
        self.sidecar_store = SidecarMetadataStore(raw_dir=raw_dir)

    def upsert(
        self,
        ids: Sequence[str],
        documents: Sequence[str],
        metadatas: Sequence[dict],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        rows = [
            (chunk_id, document, json.dumps(metadata), json.dumps(list(embedding)))
            for chunk_id, document, metadata, embedding in zip(ids, documents, metadatas, embeddings)
        ]
        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO chunks (id, document, metadata, embedding)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    document = excluded.document,
                    metadata = excluded.metadata,
                    embedding = excluded.embedding
                """,
                rows,
            )

    def query(
        self,
        embedding: list[float],
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[SourceChunk]:
        candidates: list[tuple[float, str, str, dict]] = []
        for chunk_id, document, metadata_json, stored_embedding_json in self.connection.execute(
            "SELECT id, document, metadata, embedding FROM chunks"
        ):
            metadata = json.loads(metadata_json)
            if filters and any(str(metadata.get(key)) != str(value) for key, value in filters.items()):
                continue
            score = self._cosine_similarity(embedding, json.loads(stored_embedding_json))
            candidates.append((score, chunk_id, document, metadata))

        chunks: list[SourceChunk] = []
        for score, chunk_id, document, metadata in sorted(candidates, reverse=True)[:top_k]:
            merged_metadata = self._merge_metadata(metadata or {})
            chunks.append(
                SourceChunk(
                    chunk_id=chunk_id,
                    text=document,
                    source_id=str(merged_metadata.get("source_id", "")),
                    title=str(merged_metadata.get("title", "Untitled Source")),
                    url=str(merged_metadata.get("url", "")),
                    publisher=str(merged_metadata.get("publisher", "unknown")),
                    source_type=str(merged_metadata.get("source_type", "unknown")),
                    framework=str(merged_metadata.get("framework", "general")),
                    section=str(merged_metadata.get("section", "Unknown Section")),
                    chunk_index=int(merged_metadata.get("chunk_index", 0)),
                    score=score,
                )
            )

        logger.info(
            "Retrieved %s chunks from SQLite (filters=%s, top_k=%s)",
            len(chunks),
            filters,
            top_k,
        )
        return chunks

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) FROM chunks").fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        if len(left) != len(right) or not left:
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    def _merge_metadata(self, metadata: dict) -> dict:
        sidecar = self.sidecar_store.lookup(
            url=str(metadata.get("url") or ""),
            title=str(metadata.get("title") or ""),
        )
        merged = dict(sidecar)
        for key, value in metadata.items():
            if value not in (None, ""):
                merged[key] = value
        return merged
