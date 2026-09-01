from app.retrieval.vectorstore import SqliteVectorStore


def test_sqlite_vector_store_upserts_filters_and_ranks(tmp_path):
    store = SqliteVectorStore(str(tmp_path), "test")
    store.upsert(
        ids=["closest", "other"],
        documents=["Relevant", "Different"],
        metadatas=[
            {"framework": "NIST", "title": "One", "source_id": "1"},
            {"framework": "CISA", "title": "Two", "source_id": "2"},
        ],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
    )

    assert store.count() == 2
    result = store.query([1.0, 0.0], top_k=2)
    assert [chunk.chunk_id for chunk in result] == ["closest", "other"]

    filtered = store.query([1.0, 0.0], top_k=2, filters={"framework": "CISA"})
    assert [chunk.chunk_id for chunk in filtered] == ["other"]


def test_sqlite_vector_store_upsert_replaces_existing_row(tmp_path):
    store = SqliteVectorStore(str(tmp_path), "test")
    store.upsert(["one"], ["Old"], [{"title": "Old"}], [[1.0]])
    store.upsert(["one"], ["New"], [{"title": "New"}], [[1.0]])

    assert store.count() == 1
    assert store.query([1.0], top_k=1)[0].text == "New"
