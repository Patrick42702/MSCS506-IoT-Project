import json
import time
from pathlib import Path
import serial
import paho.mqtt.client as mqtt

SERIAL_PORT = "/dev/ttyACM0"
BAUD = 115200

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC_TEMPLATE = "mscs506n/s26/dev-arduino/events"

OUT_SERIAL = Path("artifacts/serial_events.jsonl")

def main():
    OUT_SERIAL.parent.mkdir(parents=True, exist_ok=True)
    OUT_SERIAL.write_text("", encoding="utf-8")

    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)

    published = 0
    kept = 0
    parse_errors = 0
    start = time.time()

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="replace").strip()

            if not line:
                continue

            if not line.startswith("{"):
                continue

            try:
                obj = json.loads(line)
            except Exception:
                parse_errors += 1
                continue

            device_id = obj.get("device_id", "unknown")
            topic = TOPIC_TEMPLATE.format(device_id=device_id)

            client.publish(topic, payload=line, qos=0, retain=False)
            published += 1

            # with OUT_SERIAL.open("a", encoding="utf-8") as f:
            #     f.write(line + "\n")
            # kept += 1

            if published % 10 == 0:
                elapsed = time.time() - start
                rate = published / elapsed if elapsed > 0 else 0
                print(f"[bridge] published={published} parse_errors={parse_errors} rate={rate:.2f}/sec topic={topic}")

    except KeyboardInterrupt:
        print("\n[bridge] stopped")

    finally:
        try:
            ser.close()
        except Exception:
            pass
        client.disconnect()
        elapsed = time.time() - start
        print(f"[bridge] final published={published} kept={kept} parse_errors={parse_errors} seconds={elapsed:.1f}")

if __name__ == "__main__":
    main()
