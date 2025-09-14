from app.memory_vec import add_batch, query_memory, stats, drop_collection

TEST_COLLECTION = "mem_test_batch"


def test_add_batch_and_query_and_drop():
    ids = add_batch(
        ["recipe: torch = coal + stick", "fact: glass from smelting sand"],
        kind="recipe",
        metadatas=[{"src": "unit"}, {"src": "unit"}],
        collection=TEST_COLLECTION,
    )
    assert len(ids) == 2

    hits = query_memory("glass", top_k=2, collection=TEST_COLLECTION)
    assert any("glass" in h["text"] for h in hits)

    st = stats(TEST_COLLECTION)
    assert st["count"] >= 2

    assert drop_collection(TEST_COLLECTION) is True
