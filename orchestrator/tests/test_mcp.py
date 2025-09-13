from app import mcp

def test_build_and_validate_ok():
    data = mcp.build_mcp("A", "Test goal")
    ok, err = mcp.validate_mcp(data)
    assert ok and err is None

def test_build_det_key_order():
    data = mcp.build_mcp("A", "G")
    assert list(data.keys()) == ["agent_id","goal","env","inventory","skills_index","rag_snippets","team"]
