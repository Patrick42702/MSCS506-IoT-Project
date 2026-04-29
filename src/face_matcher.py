import json
import pickle
from pathlib import Path

import face_recognition
import numpy as np

KNOWN_EMBEDDINGS_FILE = Path("/home/mscs-pi5-3/MSCS506-IoT-Project/artifacts/known_face_embeddings.pkl")
FACE_CROPS_DIR = Path("/home/mscs-pi5-3/MSCS506-IoT-Project/artifacts/face_crops")
OUTPUT_FILE = Path("/home/mscs-pi5-3/MSCS506-IoT-Project/artifacts/face_match_results.json")

MATCH_THRESHOLD = 0.55

with open(KNOWN_EMBEDDINGS_FILE, "rb") as f:
    known_embeddings = pickle.load(f)

results = []

face_crop_paths = sorted(
    list(FACE_CROPS_DIR.glob("*.jpg")) +
    list(FACE_CROPS_DIR.glob("*.jpeg")) +
    list(FACE_CROPS_DIR.glob("*.png"))
)

print(f"Loaded {len(known_embeddings)} known embeddings")
print(f"Found {len(face_crop_paths)} face crops")

for path in face_crop_paths:
    print(f"\nChecking {path.name}")

    image = face_recognition.load_image_file(path)

    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        print("  No embedding created")
        results.append({
            "image_file": str(path),
            "status": "no_face_embedding",
            "identity": "unknown",
            "distance": None
        })
        continue

    test_encoding = encodings[0]

    distances = face_recognition.face_distance(known_embeddings, test_encoding)
    best_distance = float(np.min(distances))

    if best_distance <= MATCH_THRESHOLD:
        identity = "known"
    else:
        identity = "unknown"

    print(f"  Result: {identity.upper()} | distance={best_distance:.4f}")

    results.append({
        "image_file": str(path),
        "status": "ok",
        "identity": identity,
        "distance": best_distance
    })

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nSaved results to {OUTPUT_FILE}")
