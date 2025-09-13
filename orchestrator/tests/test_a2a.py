from app import a2a

def test_make_request_and_offer():
    req = a2a.make_request("A", "B", "collect", "wood", 5)
    assert req["kind"] == "REQUEST"
    off = a2a.make_offer("B", "A", "stone", 3)
    assert off["kind"] == "OFFER"
