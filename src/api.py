import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .enrich_query import SemanticCache, generate_query_variations, normalize_query
from .extract import extract_goal
from .match_deeplink import bind_deeplinks_to_goal
from .order_actions import order_actions
from .schema import ContextDeeplinkResponse, Goal
from .validators import sanitize_output, validate_context_response

app = FastAPI(title="Samsung Smart Troubleshooter")
app.state.cache = SemanticCache()
app.state.warm = True
app.state.index_ready = True


@app.on_event("startup")
def warmup() -> None:
    app.state.cache = SemanticCache()
    app.state.index_ready = True
    app.state.warm = True


@app.get("/health")
def health() -> Dict[str, str]:
    if not app.state.warm or not app.state.index_ready:
        raise HTTPException(status_code=503, detail="warming")
    return {"status": "ok"}


@app.post("/v1/troubleshoot")
def troubleshoot(payload: Dict[str, Any]) -> Dict[str, Any]:
    start = time.perf_counter()
    query = str(payload.get("query", "")).strip()
    siis_response = payload.get("siis_response")
    query_variations = generate_query_variations(query)
    normalized = normalize_query(query)
    if not query:
        result = {
            "query": query,
            "response": {"contexts": []},
            "fallback": "no_match",
            "query_variations": query_variations,
            "meta": {"latency_ms": round((time.perf_counter() - start) * 1000, 2), "cost_usd": 0.0},
        }
        return sanitize_output(result)

    cached = app.state.cache.lookup(normalized)
    if cached is not None and siis_response is None:
        response = {"query": query, "response": cached, "query_variations": query_variations, "meta": {"cache_hit": True, "latency_ms": round((time.perf_counter() - start) * 1000, 2), "cost_usd": 0.0}}
        return sanitize_output(response)

    if siis_response is None:
        result = {
            "query": query,
            "response": {"contexts": []},
            "fallback": "no_match",
            "query_variations": query_variations,
            "meta": {"cache_hit": False, "latency_ms": round((time.perf_counter() - start) * 1000, 2), "cost_usd": 0.0},
        }
        return sanitize_output(result)

    try:
        goal = extract_goal(query, siis_response)
        goal = order_actions(goal)
        goal = bind_deeplinks_to_goal(goal)
        response = {"contexts": [goal.model_dump()]}
        validate_context_response(response)
        app.state.cache.store(query, response)
        result = {
            "query": query,
            "response": response,
            "query_variations": query_variations,
            "meta": {"cache_hit": False, "latency_ms": round((time.perf_counter() - start) * 1000, 2), "cost_usd": 0.0},
        }
        return sanitize_output(result)
    except Exception:
        result = {
            "query": query,
            "response": {"contexts": []},
            "fallback": "no_match",
            "query_variations": query_variations,
            "meta": {"cache_hit": False, "latency_ms": round((time.perf_counter() - start) * 1000, 2), "cost_usd": 0.0},
        }
        return sanitize_output(result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=False)
