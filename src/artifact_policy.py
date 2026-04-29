from pathlib import Path

ARTIFACTS_DIR = Path("artifacts")

# Files that SHOULD be cleared at the start of a fresh run
CLEAR_EACH_RUN = [
    "face_candidates.json",
    "face_crops.json",
    "person_candidates.json"
    "face_match_results.json",
    "latest_detection.txt",
    "vision_events.jsonl",
]

# Files that should NEVER be cleared automatically
NEVER_CLEAR = [
    "pipeline_log.jsonl",
]

def clear_run_artifacts():
    ARTIFACTS_DIR.mkdir(exist_ok=True)

    for filename in CLEAR_EACH_RUN:
        path = ARTIFACTS_DIR / filename
        path.write_text("", encoding="utf-8")
        print(f"Cleared: {path}")

    for filename in NEVER_CLEAR:
        path = ARTIFACTS_DIR / filename
        if not path.exists():
            path.touch()
            print(f"Created persistent log: {path}")
        else:
            print(f"Kept persistent log: {path}")
