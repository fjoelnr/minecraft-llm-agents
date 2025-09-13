from orchestrator.app import mcp

def test_build_and_validate():
    data = mcp.build_mcp("A", "Test goal")
    assert mcp.validate_mcp(data)
