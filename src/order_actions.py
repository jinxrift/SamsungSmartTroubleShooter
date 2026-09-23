from typing import List

from .schema import Action, Goal, actionCategory


def category_order(action: Action) -> int:
    order = {"auto": 0, "manual": 1, "critical": 2}
    return order.get(str(action.category).lower(), 1)


def order_actions(goal: Goal) -> Goal:
    ordered = sorted(goal.actions, key=category_order)
    goal.actions = ordered
    return goal


def bundle_same_screen_actions(goal: Goal) -> Goal:
    bundled: List[Action] = []
    for action in goal.actions:
        if not bundled:
            bundled.append(action)
            continue
        previous = bundled[-1]
        if len(previous.stepGroups) == 1 and len(action.stepGroups) == 1:
            previous.stepGroups.extend(action.stepGroups)
        else:
            bundled.append(action)
    goal.actions = bundled
    return goal
