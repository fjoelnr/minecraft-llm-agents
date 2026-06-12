"""Tests for the vertical-slice hardening: action coercion + obs->MCP mapping."""

from app.llm import coerce_action, coerce_skill
from app.mcp import build_mcp_from_obs
from app.schemas import Action


def test_coerce_skill_basic_and_flat_args():
    s = coerce_skill({"skill": "craft", "item": "wooden_pickaxe", "count": 1})
    assert s == {"skill": "craft", "args": {"item": "wooden_pickaxe", "count": 1}}


def test_coerce_skill_name_variants_and_nested_args():
    s = coerce_skill({"action": "collect", "args": {"type": "spruce_log", "count": 3}})
    assert s["skill"] == "collect"
    assert s["args"]["type"] == "spruce_log"


def test_coerce_skill_target_aliases_item():
    s = coerce_skill({"skill": "craft", "target": "stick"})
    assert s["args"]["item"] == "stick"


def test_coerce_skill_unknown_defaults_to_chat():
    assert coerce_skill({"skill": "fly_to_moon"})["skill"] == "chat"
    assert coerce_skill("gibberish")["skill"] == "chat"


def test_coerce_action_key_variant():
    # model used "action" instead of "type" — must not lose the decision
    a = coerce_action({"action": "mine", "target": "oak_log", "qty": 3})
    assert Action(**a).normalize() == {"type": "mine", "target": "oak_log", "qty": 3}


def test_coerce_chat_message_alias():
    a = coerce_action({"type": "chat", "message": "hi"})
    assert a["type"] == "chat"
    assert a["text"] == "hi"


def test_coerce_nested_action_object():
    a = coerce_action({"action": {"type": "move", "blocks": 4}})
    assert a == {"type": "move", "blocks": 4}


def test_coerce_unknown_defaults_to_chat():
    assert coerce_action({"foo": "bar"})["type"] == "chat"
    assert coerce_action("just a string")["type"] == "chat"


def test_coerce_clamps_quantities():
    assert coerce_action({"type": "mine", "target": "stone", "qty": 999})["qty"] == 8
    assert coerce_action({"type": "move", "blocks": 999})["blocks"] == 10


def test_build_mcp_from_obs_maps_fields():
    obs = {
        "pos": [1, 2, 3],
        "time_of_day": "night",
        "biome": "plains",
        "nearby": ["cow"],
        "inventory": {"oak_log": 2},
    }
    mcp = build_mcp_from_obs("A", "goal", obs)
    assert mcp["agent_id"] == "A"
    assert mcp["env"]["pos"] == [1, 2, 3]
    assert mcp["env"]["nearby"] == ["cow"]
    assert mcp["inventory"] == {"oak_log": 2}


def test_build_mcp_from_obs_tolerates_missing():
    mcp = build_mcp_from_obs("A", "goal", {})
    assert mcp["env"]["pos"] == [0, 64, 0]
    assert mcp["inventory"] == {}
    assert mcp["team"] == {"teammates": [], "messages": []}


def test_build_mcp_from_obs_maps_team_context():
    obs = {
        "pos": [1, 2, 3],
        "teammates": ["Agent2@[5,70,9]"],
        "recent_chat": ["Agent2: ich sammle Holz"],
    }
    mcp = build_mcp_from_obs("Agent1", "goal", obs)
    assert mcp["team"]["teammates"] == ["Agent2@[5,70,9]"]
    assert mcp["team"]["messages"] == ["Agent2: ich sammle Holz"]
