from app.models.source import SourceChunk
from app.ranking.reranker import CrossEncoderReranker, MetadataBoostingReranker
from app.retrieval.search import RetrievalService


class FakeEmbeddingClient:
    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def query(self, embedding: list[float], top_k: int, filters: dict[str, str] | None = None) -> list[SourceChunk]:
        assert embedding == [0.1, 0.2, 0.3]
        assert top_k == 3
        assert filters == {"framework": "NIST"}
        return [
            SourceChunk(
                chunk_id="1",
                text="protective controls",
                source_id="src1",
                title="NIST Protect",
                url="/tmp/doc.md",
                publisher="NIST",
                source_type="md",
                framework="NIST",
                section="Protect",
                chunk_index=0,
                score=0.8,
            )
        ]


class FakeCrossEncoder:
    def predict(self, pairs):
        return [0.1 if "generic" in text else 0.9 for _, text in pairs]


def test_cross_encoder_reranker_uses_query_document_scores() -> None:
    reranker = CrossEncoderReranker(model_name="unused", model=FakeCrossEncoder())
    chunks = [
        SourceChunk(
            chunk_id="1",
            text="generic",
            source_id="s1",
            title="Doc 1",
            url="a",
            publisher="Publisher A",
            source_type="txt",
            framework="general",
            section="Introduction",
            chunk_index=0,
            score=0.55,
        ),
        SourceChunk(
            chunk_id="2",
            text="framework",
            source_id="s2",
            title="Doc 2",
            url="b",
            publisher="Publisher B",
            source_type="md",
            framework="NIST",
            section="Protect",
            chunk_index=1,
            score=0.53,
        ),
    ]

    reranked = reranker.rerank(query="framework guidance", chunks=chunks, limit=2)
    assert reranked[0].chunk_id == "2"
    assert reranked[0].rerank_score == 0.9


def test_metadata_boosting_reranker_is_explicit_fallback() -> None:
    reranker = MetadataBoostingReranker()
    chunks = [
        SourceChunk(
            chunk_id="1",
            text="generic",
            source_id="s1",
            title="Doc 1",
            url="a",
            publisher="Publisher A",
            source_type="txt",
            framework="general",
            section="Introduction",
            chunk_index=0,
            score=0.55,
        ),
        SourceChunk(
            chunk_id="2",
            text="framework",
            source_id="s2",
            title="Doc 2",
            url="b",
            publisher="Publisher B",
            source_type="md",
            framework="NIST",
            section="Protect",
            chunk_index=1,
            score=0.53,
        ),
    ]
    reranked = reranker.rerank(query="framework guidance", chunks=chunks, limit=2)
    assert reranked[0].chunk_id == "2"


def test_retrieval_service_uses_embeddings_and_filters() -> None:
    service = RetrievalService(
        vector_store=FakeVectorStore(),
        embedding_client=FakeEmbeddingClient(),
        top_k=3,
    )
    result = service.retrieve("What does NIST Protect mean?", filters={"framework": "NIST"})
    assert len(result) == 1
    assert result[0].title == "NIST Protect"
    assert result[0].publisher == "NIST"


def test_retrieval_service_can_filter_by_score() -> None:
    service = RetrievalService(
        vector_store=FakeVectorStore(),
        embedding_client=FakeEmbeddingClient(),
        top_k=3,
    )
    result = service.retrieve(
        "What does NIST Protect mean?",
        filters={"framework": "NIST"},
        min_score=0.85,
    )
    assert result == []


def test_seeded_retrieval_fixture_catches_wrong_expected_framework() -> None:
    service = RetrievalService(
        vector_store=FakeVectorStore(),
        embedding_client=FakeEmbeddingClient(),
        top_k=3,
    )

    result = service.retrieve("What does NIST Protect mean?", filters={"framework": "NIST"})

    assert result[0].framework == "NIST"
    assert result[0].framework != "CISA"
