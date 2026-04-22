import json
import time
from pathlib import Path

import subprocess

import cv2

INPUT_JSON = Path("artifacts/person_candidates.json")
OUTPUT_JSON = Path("artifacts/face_candidates.json")

# OpenCV built-in Haar cascade for frontal face detection
CASCADE_PATH = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"


def load_json(path: Path):
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    data = load_json(INPUT_JSON)

    if data is None:
        print(f"Input file not found: {INPUT_JSON}")
        return

    image_files = data.get("images", [])

    face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    if face_cascade.empty():
        print("Failed to load Haar cascade face detector.")
        return

    results = []

    for image_file in image_files:
        image_path = Path(image_file)

        result = {
            "image_file": str(image_path),
            "face_found": False,
            "face_count": 0,
            "faces": []
        }

        if not image_path.exists():
            result["error"] = "image_not_found"
            results.append(result)
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            result["error"] = "image_unreadable"
            results.append(result)
            continue

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        if len(faces) > 0:
            result["face_found"] = True
            result["face_count"] = int(len(faces))
            result["faces"] = [
                {
                    "x": int(x),
                    "y": int(y),
                    "w": int(w),
                    "h": int(h)
                }
                for (x, y, w, h) in faces
            ]

        results.append(result)

    output = {
        "run_ts_ms": int(time.time() * 1000),
        "source_file": str(INPUT_JSON),
        "face_candidate_count": sum(1 for r in results if r["face_found"]),
        "result_count": len(results),
        "results": results
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(results)} image result(s) to {OUTPUT_JSON}")
    print(f"Images with at least one face: {output['face_candidate_count']}")
    
    result = subprocess.run(
        ["python3", "src/face_cropper.py"],
        capture_output=True,
        text=True
    )

    print("Face cropper output:")
    print(result.stdout)

    if result.stderr:
        print("Errors from face cropper:")
        print(result.stderr)


if __name__ == "__main__":
    main()
