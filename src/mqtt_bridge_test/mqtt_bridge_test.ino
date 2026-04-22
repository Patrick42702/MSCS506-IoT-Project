// ldr_events.ino
// Telemetry + events for LDR using smoothing (avg 5), cooldown, and hysteresis.

const char* DEVICE_ID = "muller-arduino-01";
const char* SENSOR_NAME = "ldr";
const char* UNIT_NAME = "adc";
const char* RULE_NAME = "ldr_hysteresis_v1";

const int PIN_LDR = A0;
const unsigned long PERIOD_MS = 500;

const int WIN = 5;                     // moving average window
const unsigned long COOLDOWN_MS = 1000;

// Pick these based on your quick measurements:

// Covered value: 610
// Uncovered value: 256

int THRESHOLD_LO = 300;  // bright trigger
int THRESHOLD_HI = 800;  // dark trigger

unsigned long seq = 0;
unsigned long event_id = 0;
unsigned long last_sample_ms = 0;
unsigned long last_event_ms = 0;

int buf[WIN];
int idx = 0;
long sum = 0;

bool is_dark = false; // state

void setup() {
  Serial.begin(115200);
  delay(1000);
  for (int i = 0; i < WIN; i++) buf[i] = 0;
  Serial.println("BOOT");
}

int read_smoothed() {
  int raw = analogRead(PIN_LDR);
  sum -= buf[idx];
  buf[idx] = raw;
  sum += buf[idx];
  idx = (idx + 1) % WIN;
  return (int)(sum / WIN);
}

void print_telemetry(unsigned long now, int smoothed) {
  Serial.print("{\"device_id\":\"");
  Serial.print(DEVICE_ID);
  Serial.print("\",\"ts_ms\":");
  Serial.print(now);
  Serial.print(",\"seq\":");
  Serial.print(seq);
  Serial.print(",\"sensor\":\"");
  Serial.print(SENSOR_NAME);
  Serial.print("\",\"value\":");
  Serial.print(smoothed);
  Serial.print(",\"unit\":\"");
  Serial.print(UNIT_NAME);
  Serial.println("\"}");
}

void print_event(unsigned long now, const char* type, int smoothed) {
  Serial.print("{\"device_id\":\"");
  Serial.print(DEVICE_ID);
  Serial.print("\",\"ts_ms\":");
  Serial.print(now);
  Serial.print(",\"event_id\":");
  Serial.print(event_id);
  Serial.print(",\"event_type\":\"");
  Serial.print(type);
  Serial.print("\",\"sensor\":\"");
  Serial.print(SENSOR_NAME);
  Serial.print("\",\"value\":");
  Serial.print(smoothed);
  Serial.print(",\"rule\":\"");
  Serial.print(RULE_NAME);
  Serial.print("\",\"threshold_hi\":");
  Serial.print(THRESHOLD_HI);
  Serial.print(",\"threshold_lo\":");
  Serial.print(THRESHOLD_LO);
  Serial.print(",\"cooldown_ms\":");
  Serial.print(COOLDOWN_MS);
  Serial.println("}");
  event_id++;
  last_event_ms = now;
}

void loop() {
  unsigned long now = millis();
  if (now - last_sample_ms < PERIOD_MS) return;
  last_sample_ms = now;

  int smoothed = read_smoothed();

  // Telemetry stream
  // print_telemetry(now, smoothed);
  seq++;

  // Cooldown
  if (now - last_event_ms < COOLDOWN_MS) return;

  // Hysteresis events
  if (!is_dark && smoothed <= THRESHOLD_LO) {
    is_dark = true;
    print_event(now, "bright", smoothed);
  } else if (is_dark && smoothed >= THRESHOLD_HI) {
    is_dark = false;
    print_event(now, "dark", smoothed);
  }
}

