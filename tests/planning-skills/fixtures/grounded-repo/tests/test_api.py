from app.api import profiles


def test_lookup_returns_name():
    out = profiles.lookup_profile("p-1")
    assert out["name"] == "n-p-1"
