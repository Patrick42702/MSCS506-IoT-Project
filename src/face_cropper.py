import json
import time
from pathlib import Path

import cv2

INPUT_JSON = Path("artifacts/face_candidates.json")
OUTPUT_JSON = Path("artifacts/face_crops.json")
OUTPUT_DIR = Path("artifacts/face_crops")


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

    results = data.get("results", [])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    crops = []

    for entry in results:
        image_file = entry.get("image_file")
        face_found = entry.get("face_found", False)
        faces = entry.get("faces", [])

        if not image_file or not face_found or not faces:
            continue

        image_path = Path(image_file)

        if not image_path.exists():
            print(f"Skipping missing image: {image_path}")
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            print(f"Skipping unreadable image: {image_path}")
            continue

        image_h, image_w = image.shape[:2]
        stem = image_path.stem

        for i, face in enumerate(faces):
            x = int(face["x"])
            y = int(face["y"])
            w = int(face["w"])
            h = int(face["h"])

            # Clamp crop coordinates so they stay inside image bounds
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(image_w, x + w)
            y2 = min(image_h, y + h)

            if x2 <= x1 or y2 <= y1:
                print(f"Skipping invalid crop in {image_path}")
                continue

            face_crop = image[y1:y2, x1:x2]

            crop_filename = f"{stem}_face{i}.jpg"
            crop_path = OUTPUT_DIR / crop_filename

            success = cv2.imwrite(str(crop_path), face_crop)
            if not success:
                print(f"Failed to save crop: {crop_path}")
                continue

            crops.append({
                "source_image": str(image_path),
                "crop_file": str(crop_path),
                "face_index": i,
                "bbox": {
                    "x": x1,
                    "y": y1,
                    "w": x2 - x1,
                    "h": y2 - y1
                }
            })

    output = {
        "run_ts_ms": int(time.time() * 1000),
        "source_file": str(INPUT_JSON),
        "face_crop_count": len(crops),
        "crops": crops
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(crops)} face crop(s) to {OUTPUT_JSON}")
    print(f"Saved cropped face images in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()