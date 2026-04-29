import json
import time
from datetime import datetime
from pathlib import Path
import threading
import subprocess

import paho.mqtt.client as mqtt

from picamera2 import Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics

from artifact_policy import clear_run_artifacts


MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent

ARTIFACTS_DIR = BASE_DIR / "artifacts"
INITIAL_CAPTURES_DIR = ARTIFACTS_DIR / "initial_captures"

OUT = ARTIFACTS_DIR / "vision_events.jsonl"
PIPELINE_LOG = ARTIFACTS_DIR / "pipeline_log.jsonl"
LATEST_DETECTIONS = ARTIFACTS_DIR / "latest_detections.txt"

PERSON_EXTRACTOR_SCRIPT = SRC_DIR / "person_candidate_extractor.py"

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC = "mscs506n/s26/dev-arduino/events"

THRESHOLD = 0.55
PIPELINE_OK_THRESHOLD = 0.70
RECORDING_SECONDS = 20

processing_lock = threading.Lock()


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
        
def on_message(client, userdata, msg):
    locked = processing_lock.acquire(blocking=False)

    if locked:
        raw_msg = msg.payload.decode()
        event_json = json.loads(raw_msg)
        print(f"Trigger received: {msg.payload.decode()}. Starting background thread.")

        if event_json["event"] == "intruder_criteria_met":

            # start main on its own thread so we can keep
            t = threading.Thread(target=run_camera_with_lock)
            t.start()
    else:
        print("Camera busy. Message ignored.")


def run_camera_with_lock():
    try:
        main()
    finally:
        processing_lock.release()
        print("Camera task complete. Lock released.")


def arduino_trigger():
    client = mqtt.Client()
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.subscribe(TOPIC)
    client.loop_start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        client.loop_stop()
        print("Stopped MQTT listener.")

def main():
    clear_run_artifacts()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    INITIAL_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    # Reset these files each run.
    # pipeline_log.jsonl is intentionally never cleared here.
    OUT.write_text("", encoding="utf-8")
    LATEST_DETECTIONS.write_text("", encoding="utf-8")

    imx500 = IMX500(MODEL)
    intrinsics = imx500.network_intrinsics

    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "object detection"

    intrinsics.update_with_defaults()
    labels = intrinsics.labels or []

    with Picamera2(imx500.camera_num) as picam2:
        config = picam2.create_preview_configuration(
            controls={"FrameRate": intrinsics.inference_rate},
            buffer_count=12
        )

        imx500.show_network_fw_progress_bar()
        picam2.start(config, show_preview=False)
        time.sleep(2)

        event_id = 1
        last_capture_second = -1
        current_second_image_path = None
        
        start_monotonic = time.monotonic()

        try:
            while True:
                elapsed = time.monotonic() - start_monotonic

                if elapsed >= RECORDING_SECONDS:
                    break

                current_second = int(elapsed)

                # Reset shared capture path when we enter a new second.
                if current_second != last_capture_second:
                    current_second_image_path = None

                metadata = picam2.capture_metadata()
                outputs = imx500.get_outputs(metadata, add_batch=True)

                if outputs is None:
                    continue

                boxes, scores, classes = outputs[0][0], outputs[1][0], outputs[2][0]

                if intrinsics.bbox_normalization:
                    input_w, input_h = imx500.get_input_size()
                    boxes = boxes / input_h

                if intrinsics.bbox_order == "xy":
                    boxes = boxes[:, [1, 0, 3, 2]]

                for box, score, category in zip(boxes, scores, classes):
                    score = float(score)

                    # Ignore extremely weak detections entirely.
                    if score < THRESHOLD:
                        continue
                        
                    label = str(category)
                    if labels and int(category) < len(labels):
                        label = labels[int(category)]

                    ts_ms = int(time.time() * 1000)
                    pipeline_status = "ok" if score >= PIPELINE_OK_THRESHOLD else "no_detection"

                    image_path = None

                    # Only high-confidence detections create/use an image.
                    if score >= PIPELINE_OK_THRESHOLD:
                        if current_second_image_path is None:
                            image_path = INITIAL_CAPTURES_DIR / f"capture_{current_second:02d}.jpg"
                            picam2.capture_file(str(image_path))

                            current_second_image_path = image_path
                            last_capture_second = current_second
                        else:
                            image_path = current_second_image_path

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
                        "image_file": str(image_path) if image_path else None,
                        "rule": "imx500_mobilenet_ssd_v1"
                    }

                    with OUT.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(record) + "\n")

                    if score >= PIPELINE_OK_THRESHOLD:
                        append_latest_detection(label, score, ts_ms)

                    append_pipeline_log(
                        status=pipeline_status,
                        event_id=event_id,
                        label=label,
                        confidence=score,
                        ts_ms=ts_ms
                    )

                    event_id += 1

            print(f"Monitoring session complete: ran for {RECORDING_SECONDS} seconds")
            print("Detection records written to", OUT)

        finally:
            picam2.stop()

            try:
                picam2.stop_encoder()
            except Exception:
                pass

            print("Running person candidate extractor...")
            subprocess.run(
                ["python3", str(PERSON_EXTRACTOR_SCRIPT)],
                cwd=str(BASE_DIR),
                check=False
            )


if __name__ == "__main__":
    arduino_trigger()
