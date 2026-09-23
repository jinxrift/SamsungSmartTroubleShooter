from src.extract import extract_goal
from src.validators import sanitize_text, validate_goal


def test_extract_goal_matches_required_structure():
    goal = extract_goal(
        "My screen is blank on my Galaxy phone",
        {
            "title": "Blank or black display on a Samsung phone or tablet",
            "content": "## Step 1: Check the charger and USB cable. ## Step 2: Force a restart. ## Step 3: Charge your device for 1 hour.",
        },
    )
    assert goal.goal.startswith("Follow these steps to")
    assert 2 <= len(goal.title.split()) <= 9
    assert len(goal.actions) >= 1
    assert goal.actions[0].description.startswith("It will")
    assert validate_goal(goal)


def test_validator_rejects_noncompliant_goal():
    invalid = {
        "goal": "do something else",
        "title": "This is way too long for a valid title and includes too many words in the field",
        "actions": [{
            "actionName": "Bad action",
            "description": "Fix the issue quickly.",
            "stepGroups": [{"steps": ["One step", "Two step", "Three step"]}]
        }],
        "score": 0.8,
    }
    assert validate_goal(invalid) is False


def test_sanitize_text_removes_markdown_and_urls():
    sample = "Check https://example.com and [Settings](https://example.com/settings) before you proceed."
    cleaned = sanitize_text(sample)
    assert "http" not in cleaned.lower()
    assert "Settings" in cleaned
    assert "[" not in cleaned
