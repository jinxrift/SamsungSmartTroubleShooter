import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .schema import Deeplink, Goal, ValidationDeepLink

_ROOT = Path(__file__).resolve().parents[1]


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _catalog_text(entry: Dict[str, Any]) -> str:
    return " ".join(
        filter(
            None,
            [
                entry.get("description", ""),
                entry.get("message", ""),
                entry.get("qna_description", ""),
            ],
        )
    )


def load_catalog() -> List[Dict[str, Any]]:
    path = _ROOT / "samples" / "deeplinks.json"
    payload = json.loads(path.read_text())
    return payload.get("deeplinks", [])


def build_bm25_index() -> Dict[str, Any]:
    entries = load_catalog()
    docs = [_catalog_text(entry) for entry in entries]
    tokens = [_tokenize(doc) for doc in docs]
    doc_freq: Dict[str, int] = defaultdict(int)
    for doc_tokens in tokens:
        seen = set()
        for token in doc_tokens:
            if token not in seen:
                seen.add(token)
                doc_freq[token] += 1
    avgdl = sum(len(doc_tokens) for doc_tokens in tokens) / len(tokens) if tokens else 1.0
    k1 = 1.5
    b = 0.75
    return {"docs": entries, "texts": docs, "tokens": tokens, "doc_freq": doc_freq, "avgdl": avgdl, "k1": k1, "b": b, "N": len(entries)}


def build_dense_index() -> Dict[str, Any]:
    entries = load_catalog()
    docs = [_catalog_text(entry) for entry in entries]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    matrix = vectorizer.fit_transform(docs)
    return {"docs": entries, "texts": docs, "vectorizer": vectorizer, "matrix": matrix}


def _bm25_score(query_tokens: Sequence[str], doc_tokens: Sequence[str], index: Dict[str, Any], doc_idx: int) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    score = 0.0
    for token in set(query_tokens):
        tf = doc_tokens.count(token)
        if tf == 0:
            continue
        df = index["doc_freq"].get(token, 0)
        idf = math.log(((index["N"] - df + 0.5) / (df + 0.5)) + 1.0)
        denom = tf + index["k1"] * (1.0 - index["b"] + index["b"] * (len(doc_tokens) / index["avgdl"]))
        score += idf * ((index["k1"] + 1.0) * tf) / denom
    return score


def _dense_scores(query: str, dense_index: Dict[str, Any]) -> List[float]:
    if not query:
        return [0.0 for _ in dense_index["docs"]]
    sparse = dense_index["vectorizer"].transform([query])
    return cosine_similarity(sparse, dense_index["matrix"])[0].tolist()


def merge_and_rerank(query: str, bm25_docs: Sequence[Dict[str, Any]], dense_docs: Sequence[Dict[str, Any]], top_k: int = 5) -> Dict[str, Any]:
    query_tokens = _tokenize(query)
    bm25_index = build_bm25_index()
    dense_index = build_dense_index()
    bm25_scores = []
    for doc_idx, entry in enumerate(bm25_docs):
        token_overlap = len(set(query_tokens) & set(bm25_index["tokens"][doc_idx]))
        bm25_score = _bm25_score(query_tokens, bm25_index["tokens"][doc_idx], bm25_index, doc_idx)
        # add a small specificity bonus to favor exact screens over parent menus
        specificity_bonus = min(0.2, token_overlap * 0.03)
        bm25_scores.append((entry, bm25_score + specificity_bonus))

    dense_scores = _dense_scores(query, dense_index)
    combined: Dict[str, float] = {}
    for idx, entry in enumerate(bm25_docs):
        score = 0.0
        if idx < len(dense_scores):
            score += dense_scores[idx] * 0.7
        score += next((s for e, s in bm25_scores if e == entry), 0.0) * 0.3
        combined[entry.get("deeplink", "")] = score

    ranked = sorted(
        [(entry, combined.get(entry.get("deeplink", ""), 0.0)) for entry in bm25_docs],
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]
    candidates = [{**entry, "score": float(score), "source": "merged"} for entry, score in ranked]
    best = candidates[0] if candidates else {"deeplink": "bixby://dummy_positive", "message": "Open the relevant Settings screen", "description": "Generic placeholder for a relevant Settings screen", "score": 0.0}
    return {"best": best, "candidates": candidates}


def match_deeplink_for_text(text: str, top_k: int = 3) -> Dict[str, Any]:
    if not text:
        return {
            "deeplink": "bixby://dummy_positive",
            "description": "Generic placeholder for a relevant Settings screen",
            "message": "Open the relevant Settings screen",
            "originalType": "placeholder",
            "score": 0.0,
            "validation": None,
        }

    bm25_index = build_bm25_index()
    dense_index = build_dense_index()
    merged = merge_and_rerank(text, bm25_index["docs"], dense_index["docs"], top_k=top_k)
    best = merged["best"]
    score = float(best.get("score", 0.0))
    if score <= 0.08:
        return {
            "deeplink": "bixby://dummy_positive",
            "description": "Generic placeholder for a relevant Settings screen",
            "message": "Open the relevant Settings screen",
            "originalType": "placeholder",
            "score": 0.0,
            "validation": None,
        }

    return {
        "deeplink": best.get("deeplink", "bixby://dummy_positive"),
        "description": best.get("description", ""),
        "message": best.get("message", ""),
        "originalType": best.get("originalType", "onClickURL"),
        "score": score,
        "validation": best.get("validation"),
    }


def bind_deeplinks_to_goal(goal: Goal) -> Goal:
    for action in goal.actions:
        for step_group in action.stepGroups:
            combined_text = " ".join(step_group.steps)
            matched = match_deeplink_for_text(combined_text)
            validation = matched.get("validation") or {}
            step_group.actionableDeeplink = Deeplink(
                deeplink=matched["deeplink"],
                description=matched["description"],
                message=matched["message"],
                originalType=matched["originalType"],
            )
            if validation:
                step_group.validationDeeplink = ValidationDeepLink(
                    deeplink=validation.get("deeplink", "bixby://dummy_positive"),
                    key=validation.get("key", "Check setting"),
                    resultType=validation.get("resultType"),
                    condition=validation.get("condition"),
                    value=validation.get("value"),
                )
    return goal


if __name__ == "__main__":
    print(match_deeplink_for_text("switch time format to 24 hour display"))
