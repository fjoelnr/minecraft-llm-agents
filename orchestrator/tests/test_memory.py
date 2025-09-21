from app import memory


def test_memory_add_and_query():
    memory.add_memory("recipe: planks = log * 4")
    res = memory.query_memory("planks")
    assert len(res) > 0
