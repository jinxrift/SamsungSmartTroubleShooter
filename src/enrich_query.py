import re
from typing import Any, Dict, List


def normalize_query(query: str) -> str:
    value = (query or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def generate_query_variations(query: str) -> List[str]:
    base = normalize_query(query)
    if not base:
        return []
    variants = {
        "canonical": base,
        "formal": f"Troubleshooting for {base}",
        "casual": f"My {base} is acting up",
        "keyword": " ".join(base.split()[:4]),
        "typo": base.replace("screen", "scren").replace("phone", "phne"),
        "short": " ".join(base.split()[:3]),
        "issue": f"device {base}",
        "display": f"{base} blank display",
        "fix": f"how to fix {base}",
    }
    ordered = [v for v in variants.values() if v]
    seen = set()
    output = []
    for item in ordered:
        item = re.sub(r"\s+", " ", item).strip()
        if item and item not in seen:
            output.append(item)
            seen.add(item)
    while len(output) < 8:
        output.append(base)
    return output[:10]


class SemanticCache:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def _similarity(self, left: str, right: str) -> float:
        left_tokens = set(normalize_query(left).split())
        right_tokens = set(normalize_query(right).split())
        if not left_tokens or not right_tokens:
            return 0.0
        union = left_tokens | right_tokens
        if not union:
            return 0.0
        inter = left_tokens & right_tokens
        return len(inter) / len(union)

    def lookup(self, query: str) -> Any:
        qn = normalize_query(query)
        best_match = None
        best_score = 0.0
        for key, payload in self._cache.items():
            if key == qn:
                return payload
            score = self._similarity(qn, key)
            if score >= 0.75 and score > best_score:
                best_match = payload
                best_score = score
        return best_match

    def store(self, query: str, payload: Any) -> None:
        self._cache[normalize_query(query)] = payload

    @property
    def size(self) -> int:
        return len(self._cache)
