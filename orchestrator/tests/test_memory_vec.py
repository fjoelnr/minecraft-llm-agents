from app.memory_vec import add_memory, query_memory


def test_memory_vec_add_and_query_roundtrip():
    mid = add_memory("recipe: planks = 4 * log", kind="recipe", metadata={"mc": "1.19"})
    assert mid.startswith("m_")
    hits = query_memory("planks")
    assert any("planks" in h["text"] for h in hits)
