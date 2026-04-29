import json
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

FACE_RESULTS_FILE = PROJECT_ROOT / "artifacts" / "face_match_results.json"
FACE_CROPS_DIR = PROJECT_ROOT / "artifacts" / "face_crops"
INTRUDER_LOG_FILE = PROJECT_ROOT / "artifacts" / "intruder_log.txt"


EMAIL_ADDRESS = "mitchpatrick16@gmail.com"
EMAIL_PASSWORD = "rzxc yhvb yfmh pnds"

OWNER_TEXT_ADDRESSES = [
    "8452757228@vtext.com",
    "8457979008@vtext.com",
    "mitchlevy30@gmail.com",
    "Patrick.Muller1@marist.edu"
]


def load_face_results():
    if not FACE_RESULTS_FILE.exists():
        return []

    try:
        with open(FACE_RESULTS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def count_face_crops():
    if not FACE_CROPS_DIR.exists():
        return 0

    image_extensions = {".jpg", ".jpeg", ".png"}
    return sum(
        1 for file in FACE_CROPS_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in image_extensions
    )


def write_log(message):
    INTRUDER_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(INTRUDER_LOG_FILE, "a") as f:
        f.write(message + "\n")


def send_texts(message):
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        for address in OWNER_TEXT_ADDRESSES:
            msg = MIMEText(message)
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = address
            msg["Subject"] = "Alert"

            server.sendmail(EMAIL_ADDRESS, address, msg.as_string())
            print(f"Sent email-to-text attempt to {address}")
            time.sleep(2)
            
def decide_security_event(results, face_crop_count):
    if face_crop_count == 0:
        return "no_person"

    has_intruder = any(
        result.get("status") == "ok" and result.get("identity") == "unknown"
        for result in results
    )

    if has_intruder:
        return "intruder"

    has_known_person = any(
        result.get("status") == "ok" and result.get("identity") == "known"
        for result in results
    )

    if has_known_person:
        return "known_person"

    all_status_not_ok = (
        len(results) > 0
        and all(result.get("status") != "ok" for result in results)
    )

    if all_status_not_ok:
        return "unreadable_person"

    return "no_person"

def main():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%I:%M:%S %p")

    results = load_face_results()
    face_crop_count = count_face_crops()

    event_type = decide_security_event(results, face_crop_count)

    if event_type == "intruder":
        message = f"Intruder detected on {date_str} at {time_str}!"
        write_log(message)
        send_texts(message)
        print(message)

    elif event_type == "known_person":
        message = f"Known person detected on {date_str} at {time_str}."
        write_log(message)
        print(message)

    elif event_type == "no_person":
        message = f"No person detected on {date_str} at {time_str}."
        write_log(message)
        print(message)

    elif event_type == "unreadable_person":
        log_message = f"Unreadable person detected on {date_str} at {time_str}."
        text_message = f"Possible intruder detected on {date_str} at {time_str}!"

        write_log(log_message)
        send_texts(text_message)
        
        print(log_message)
        print(text_message)


if __name__ == "__main__":
    main()
