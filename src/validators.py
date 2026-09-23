import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .schema import Action, ContextDeeplinkResponse, Goal, StepGroup, actionCategory

GOAL_RE = re.compile(r"^Follow these steps to (?:troubleshoot|resolve|fix|check|repair|use|perform) .+$")


def sanitize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"^```(?:json|python)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\[[^\]]*\]\([^\)]*\)", " ", text)
    text = re.sub(r"[\[\](){}`]+", " ", text)
    text = re.sub(r"\*+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sanitize_output(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_output(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_output(item) for key, item in value.items()}
    return value


def validate_goal(goal: Goal | Mapping[str, Any]) -> bool:
    if isinstance(goal, dict):
        payload = goal
    else:
        payload = goal.model_dump()
    goal_text = sanitize_text(payload.get("goal", ""))
    if not GOAL_RE.match(goal_text):
        return False
    title = sanitize_text(payload.get("title", "")).split()
    if not 2 <= len(title) <= 9:
        return False
    actions = payload.get("actions", [])
    if not actions:
        return False
    for action in actions:
        if not isinstance(action, Mapping):
            return False
        description = sanitize_text(action.get("description", ""))
        if not description.startswith("It will"):
            return False
        words = description.split()
        if not 8 <= len(words) <= 25:
            return False
        category = action.get("category")
        if category is not None and category not in {item.value for item in actionCategory}:
            return False
        step_groups = action.get("stepGroups", [])
        if not step_groups:
            return False
        steps = []
        for group in step_groups:
            if not isinstance(group, Mapping):
                return False
            group_steps = group.get("steps", [])
            if not isinstance(group_steps, Sequence) or not group_steps:
                return False
            steps.extend(group_steps)
        if len(steps) == 0:
            return False
    return True


def validate_context_response(payload: Any) -> ContextDeeplinkResponse:
    if isinstance(payload, ContextDeeplinkResponse):
        return payload
    if isinstance(payload, Mapping):
        if "contexts" not in payload and "response" in payload and isinstance(payload["response"], Mapping):
            payload = payload["response"]
        obj = ContextDeeplinkResponse.model_validate(payload)
        for ctx in obj.contexts:
            if not validate_goal(ctx):
                raise ValueError(f"Goal validation failed for: {ctx.goal}")
        return obj
    raise TypeError("Payload must be a mapping or ContextDeeplinkResponse")


def one_action_one_screen(goal: Goal | Mapping[str, Any]) -> bool:
    payload = goal.model_dump() if not isinstance(goal, Mapping) else goal
    for action in payload.get("actions", []):
        step_groups = action.get("stepGroups", [])
        if len(step_groups) > 1:
            all_steps = [step for group in step_groups for step in group.get("steps", [])]
            if len(all_steps) > 3:
                return False
    return True
