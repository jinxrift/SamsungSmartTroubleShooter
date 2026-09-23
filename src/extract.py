import json
import re
from typing import Any, Dict, Iterable, List, Mapping

from .schema import Action, Goal, StepGroup, actionCategory
from .validators import sanitize_text, validate_goal


def title_from_query(query: str) -> str:
    q = sanitize_text(query)
    cleaned = re.sub(r"^\d+\.\s*", "", q)
    cleaned = re.sub(r"[\"']", "", cleaned)
    words = [w for w in cleaned.lower().split() if len(w) > 2][:6]
    if not words:
        return "Device troubleshooting"
    title = " ".join(words[:4]).title()
    return title


def _score_category(text: str) -> actionCategory:
    lower = text.lower()
    if any(token in lower for token in ["factory reset", "wipe", "erase", "hard reset", "delete", "backup"]):
        return actionCategory.critical
    if any(token in lower for token in ["restart", "toggle", "enable", "disable", "clear cache", "settings", "screen lock"]):
        return actionCategory.auto
    if any(token in lower for token in ["service", "repair", "contact", "visit", "authorized", "support"]):
        return actionCategory.manual
    return actionCategory.manual


def extract_steps(text: str) -> List[str]:
    if not text:
        return []
    cleaned = sanitize_text(text)
    chunks = re.split(r"(?<=[.!?])\s+|(?<=\n)\s*", cleaned)
    steps: List[str] = []
    for chunk in chunks:
        chunk = sanitize_text(chunk)
        if not chunk:
            continue
        if len(chunk.split()) < 4:
            continue
        if chunk.lower().startswith("note:"):
            continue
        steps.append(chunk)
    if not steps:
        steps = [cleaned]
    return steps[:4]


def extract_goal(query: str, siis_response: str | Mapping[str, Any] | None) -> Goal:
    q = sanitize_text(query)
    if isinstance(siis_response, Mapping):
        content = str(siis_response.get("content", "") or siis_response.get("title", "") or "")
        title_text = str(siis_response.get("title", "") or "Device issue")
    elif isinstance(siis_response, str):
        content = siis_response
        title_text = "Device issue"
    else:
        content = ""
        title_text = "Device issue"
    base_title = title_from_query(q) or sanitize_text(title_text)
    goal_text = "Follow these steps to troubleshoot this device issue"
    steps = extract_steps(content or q)
    category = _score_category(content or q)
    action = Action(
        actionName="Review diagnostic steps",
        description="It will guide the user through the most relevant troubleshooting steps for the device issue.",
        stepGroups=[StepGroup(steps=steps, actionableDeeplink=None, validationDeeplink=None)],
        category=category,
    )
    goal = Goal(goal=goal_text, title=base_title, actions=[action], score=0.9)
    if not validate_goal(goal):
        raise ValueError("Extracted goal failed validation")
    return goal


def extract_from_samples() -> List[Goal]:
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    samples = root / "samples" / "siis_responses.json"
    payload = json.loads(samples.read_text())
    goals: List[Goal] = []
    for item in payload.get("responses", [])[:5]:
        query = item.get("original_query", "")
        response = item.get("siis_response", {})
        goals.append(extract_goal(query, response))
    return goals


if __name__ == "__main__":
    for goal in extract_from_samples():
        print(goal.model_dump_json(indent=2))
