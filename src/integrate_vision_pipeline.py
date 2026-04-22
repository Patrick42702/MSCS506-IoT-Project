import json
import time
from datetime import datetime
from pathlib import Path

from picamera2 import Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics

MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
OUT = Path("trackB/vision_events.jsonl")
PIPELINE_LOG = Path("trackB/pipeline_log.jsonl")
LATEST_DETECTIONS = Path("trackB/latest_detections.txt")

THRESHOLD = 0.55
PIPELINE_OK_THRESHOLD = 0.70
MAX_RECORDS = 5
MAX_FRAMES_WITHOUT_DETECTION = 100


def append_pipeline_log(status, event_id, label, confidence, ts_ms):
    log_record = {
        "ts_ms": ts_ms,
        "status": status,
        "source": "vision_pipeline",
        "event_id": event_id,
        "label": label,
        "confidence": round(confidence, 4)
    }

    with PIPELINE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_record) + "\n")
        
def append_latest_detection(label, confidence, ts_ms):
    dt_string = datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{dt_string} - Detected {label} with confidence {confidence:.4f}\n"

    with LATEST_DETECTIONS.open("a", encoding="utf-8") as f:
        f.write(line)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Reset only these files each run
    OUT.write_text("", encoding="utf-8")
    LATEST_DETECTIONS.write_text("", encoding="utf-8")

    # IMPORTANT: pipeline_log.jsonl is NEVER cleared

    imx500 = IMX500(MODEL)
    intrinsics = imx500.network_intrinsics

    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "object detection"

    intrinsics.update_with_defaults()
    labels = intrinsics.labels or []

    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration(
        controls={"FrameRate": intrinsics.inference_rate},
        buffer_count=12
    )
    
    imx500.show_network_fw_progress_bar()
    picam2.start(config, show_preview=False)
    time.sleep(2)

    written = 0
    event_id = 1
    frames_checked = 0

    try:
        while written < MAX_RECORDS and frames_checked < MAX_FRAMES_WITHOUT_DETECTION:
            metadata = picam2.capture_metadata()
            outputs = imx500.get_outputs(metadata, add_batch=True)

            if outputs is None:
                continue

            frames_checked += 1

            boxes, scores, classes = outputs[0][0], outputs[1][0], outputs[2][0]

            if intrinsics.bbox_normalization:
                input_w, input_h = imx500.get_input_size()
                boxes = boxes / input_h

            if intrinsics.bbox_order == "xy":
                boxes = boxes[:, [1, 0, 3, 2]]

            for box, score, category in zip(boxes, scores, classes):
                score = float(score)

                # Ignore extremely weak detections entirely
                if score < THRESHOLD:
                    continue
                    
                label = str(category)
                if labels and int(category) < len(labels):
                    label = labels[int(category)]

                ts_ms = int(time.time() * 1000)

                pipeline_status = "ok" if score >= PIPELINE_OK_THRESHOLD else "no_detection"

                image_path = None
                if score >= PIPELINE_OK_THRESHOLD:
                    image_path = f"trackB/capture_{event_id}.jpg"
                    picam2.capture_file(image_path)

                scaled = imx500.convert_inference_coords(box, metadata, picam2)

                record = {
                    "device_id": "pi-camera",
                    "ts_ms": ts_ms,
                    "event_id": event_id,
                    "event_type": "object_detected",
                    "label": label,
                    "class_id": int(category),
                    "confidence": round(score, 4),
                    "bbox": [
                        int(scaled[0]),
                        int(scaled[1]),
                        int(scaled[2]),
                        int(scaled[3])
                    ],
                    "image_file": image_path,
                    "rule": "imx500_mobilenet_ssd_v1"
                }
                
                with OUT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")

                # Only add to latest_detections if it passed pipeline threshold
                if score >= PIPELINE_OK_THRESHOLD:
                    append_latest_detection(label, score, ts_ms)

                # Always add to pipeline log for every detection above THRESHOLD
                append_pipeline_log(
                    status=pipeline_status,
                    event_id=event_id,
                    label=label,
                    confidence=score,
                    ts_ms=ts_ms
                )

                written += 1
                event_id += 1

                if written >= MAX_RECORDS:
                    break

        print("Wrote", written, "records to", OUT)

    finally:
        picam2.stop()


if __name__ == "__main__":
    main()
