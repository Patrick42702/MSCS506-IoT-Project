import face_recognition
from pathlib import Path
import pickle

KNOWN_DIR = Path("/home/mscs-pi5-3/MSCS506-IoT-Project/artifacts/known_faces")
OUTPUT_FILE = Path("/home/mscs-pi5-3/MSCS506-IoT-Project/artifacts/known_face_embeddings.pkl")

embeddings = []
image_paths = list(KNOWN_DIR.glob("*"))

print(f"Found {len(image_paths)} images")

for path in image_paths:
    print(f"Processing {path.name}")

    image = face_recognition.load_image_file(path)
    face_locations = face_recognition.face_locations(image)

    if len(face_locations) == 0:
        print("  No face detected, skipping")
        continue

    encodings = face_recognition.face_encodings(image, face_locations)

    for encoding in encodings:
        embeddings.append(encoding)

print(f"\nTotal embeddings created: {len(embeddings)}")

with open(OUTPUT_FILE, "wb") as f:
    pickle.dump(embeddings, f)

print(f"Saved embeddings to {OUTPUT_FILE}")
