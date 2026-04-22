import json
from collections import Counter
from pathlib import Path
from datetime import datetime

VISION_EVENTS = Path("trackB/vision_events.jsonl")
RECENT_COUNT = 5


def load_recent_detections(path, count=5):
    if not path.exists():
        print(f"File not found: {path}")
        return []

    with path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    records = []
    for line in lines:
        try:
            record = json.loads(line)
            records.append(record)
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON line: {line}")

    return records[-count:]

def print_recent_detections(records):
    print(f"\nMost recent {len(records)} detection record(s):")
    for i, record in enumerate(records, start=1):
        print(f"\nRecord {i}:")
        print(json.dumps(record, indent=2))


def print_count_by_label(records):
    label_counts = Counter(record.get("label", "unknown") for record in records)

    print("\nCount by object label:")
    for label, count in label_counts.items():
        print(f"{label}: {count}")

def print_highest_confidence_detection(records):
    if not records:
        print("\nNo detections available.")
        return

    best = max(records, key=lambda r: r.get("confidence", 0))

    label = best.get("label", "unknown")
    confidence = best.get("confidence", 0)
    ts_ms = best.get("ts_ms")

    if ts_ms:
        dt = datetime.fromtimestamp(ts_ms / 1000)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = "unknown time"

    print("\nHighest-confidence recent detection:")
    print(f"{label} detected with confidence {confidence:.4f} at {time_str}")

def main():
    recent_records = load_recent_detections(VISION_EVENTS, RECENT_COUNT)

    if not recent_records:
        print("No detection records found.")
        return

    print_recent_detections(recent_records)
    print_count_by_label(recent_records)
    print_highest_confidence_detection(recent_records)


if __name__ == "__main__":
    main()

