from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"

# Files cleared each run
CLEAR_FILES = [
    "face_candidates.json",
    "face_crops.json",
    "face_match_results.json",
    "latest_detections.txt",
    "vision_events.jsonl",
]

# Files that should persist
PERSISTENT_FILES = [
    "pipeline_log.jsonl",
]

# Folders cleared each run
CLEAR_FOLDERS = [
    ARTIFACTS_DIR / "initial_captures",
    ARTIFACTS_DIR / "face_crops",
]

def clear_run_artifacts():

    ARTIFACTS_DIR.mkdir(exist_ok=True)

    # Clear folders (delete + recreate)
    for folder in CLEAR_FOLDERS:
        if folder.exists():
            shutil.rmtree(folder)
            print(f"Cleared folder: {folder}")

        folder.mkdir(parents=True, exist_ok=True)

    # Clear files
    for filename in CLEAR_FILES:
        path = ARTIFACTS_DIR / filename
        path.write_text("", encoding="utf-8")
        print(f"Cleared file: {path}")

    # Ensure persistent logs exist
    for filename in PERSISTENT_FILES:
        path = ARTIFACTS_DIR / filename
        if not path.exists():
            path.touch()
            print(f"Created persistent log: {path}")
