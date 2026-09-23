from fastapi.testclient import TestClient

from src.api import app


def test_health_is_503_when_not_warmed():
    original_warm = app.state.warm
    original_index = app.state.index_ready
    app.state.warm = False
    app.state.index_ready = False
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 503
    finally:
        app.state.warm = True
        app.state.index_ready = True
        app.state.cache = app.state.cache


def test_cache_lookup_uses_similarity_and_returns_cached_payload():
    cache = app.state.cache
    cache.store("screen blank on samsung phone", {"contexts": [{"goal": "Follow these steps to troubleshoot this device issue"}]})
    hit = cache.lookup("screen blank samsung phone")
    assert hit is not None
    assert hit["contexts"][0]["goal"].startswith("Follow these steps to")
