from app.schemas import Action

def test_action_chat_ok():
    a = Action(type="chat", text="hi").normalize()
    assert a["type"] == "chat" and a["text"] == "hi"

def test_action_mine_ok():
    a = Action(type="mine", target="stone", qty=2).normalize()
    assert a["type"] == "mine" and a["qty"] == 2

def test_action_missing_fields_defaults():
    a = Action(type="craft", recipe="torch").normalize()
    assert a["type"] == "craft" and a["qty"] == 1
