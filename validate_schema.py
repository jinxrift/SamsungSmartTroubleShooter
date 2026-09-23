import json
from pathlib import Path

from pydantic import ValidationError

from src.schema import ContextDeeplinkResponse

ROOT = Path(__file__).resolve().parent


def validate_file(path: Path) -> bool:
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "response" in data and isinstance(data["response"], dict):
        payload = data["response"]
    else:
        payload = data
    if isinstance(payload, dict) and "contexts" in payload:
        ContextDeeplinkResponse.model_validate(payload)
        return True
    return False


if __name__ == "__main__":
    sample_dir = ROOT / "samples"
    candidates = sorted(sample_dir.glob("*.json"))
    ok = 0
    failed = []
    skip = {"deeplinks.json", "siis_responses.json", "queries.json"}
    for path in candidates:
        try:
            if path.name in skip:
                continue
            if validate_file(path):
                ok += 1
            else:
                failed.append((path.name, "missing contexts"))
        except Exception as exc:  # pragma: no cover - script failure reporting
            failed.append((path.name, str(exc)))
    print(f"validated: {ok} sample files")
    if failed:
        for item in failed:
            print("FAIL:", item)
        raise SystemExit(1)
