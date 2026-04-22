import json
import time
from pathlib import Path

VISION_EVENTS = Path("artifacts/vision_events.jsonl")
OUT_JSON = Path("artifacts/person_candidates.json")
PERSON_LABEL = "person"
MIN_CONFIDENCE = 0.70


def load_jsonl(path: Path):
    records = []

    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON on line {line_num}")

    return records


def main():
    records = load_jsonl(VISION_EVENTS)

    candidate_images = []
    seen = set()

    for record in records:
        label = str(record.get("label", "")).lower()
        confidence = float(record.get("confidence", 0.0))
        image_file = record.get("image_file")

        if label != PERSON_LABEL:
            continue

        if confidence <= MIN_CONFIDENCE:
            continue

        if not image_file:
            continue

        if image_file in seen:
            continue

        seen.add(image_file)
        candidate_images.append(image_file)

    output = {
        "run_ts_ms": int(time.time() * 1000),
        "source_file": str(VISION_EVENTS),
        "person_candidate_count": len(candidate_images),
        "images": candidate_images
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(candidate_images)} candidate image(s) to {OUT_JSON}")


if __name__ == "__main__":
    main()
