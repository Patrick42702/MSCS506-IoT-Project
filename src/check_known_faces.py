from pathlib import Path
import cv2

KNOWN_DIR = Path("/home/mscs-pi5-3/MSCS506-IoT-Project/artifacts/known_faces")

image_paths = sorted(
    list(KNOWN_DIR.glob("*.jpg")) +
    list(KNOWN_DIR.glob("*.jpeg")) +
    list(KNOWN_DIR.glob("*.JPG")) +
    list(KNOWN_DIR.glob("*.JPEG")) +
    list(KNOWN_DIR.glob("*.png")) +
    list(KNOWN_DIR.glob("*.PNG"))
)

print(f"Found {len(image_paths)} images")

for path in image_paths:
    img = cv2.imread(str(path))
    if img is None:
        print(f"BAD READ: {path.name}")
    else:
        h, w = img.shape[:2]
        print(f"OK: {path.name} ({w}x{h})")
