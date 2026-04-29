const int reedPin = 2;
const int photoPin = A0;

// -------------------- Magnetic sensor --------------------
int lastReedState = HIGH;

// -------------------- Photoresistor calibration --------------------
const unsigned long calibrationTimeMs = 30000; // 30 seconds
const unsigned long sampleIntervalMs = 50;    // sample every 50 ms

bool calibrated = false;
unsigned long calibrationStartTime;
unsigned long lastSampleTime = 0;

int sampleCount = 0;
double sum = 0;
double sumSquares = 0;

double lightMean = 0;
double lightStdDev = 0;

// -------------------- Detection thresholds --------------------
const double zScoreThreshold = 3.0; // higher = less sensitive
const int minRawDifference = 75;    // prevents tiny stddev false positives

// -------------------- Event timing --------------------
const unsigned long correlationWindowMs = 30000; // 30 seconds
// Change to 20000 if you want 20 seconds instead

unsigned long lastMagneticEventTime = 0;
unsigned long lastLightEventTime = 0;

bool magneticEventActive = false;
bool lightEventActive = false;

void setup() {
  pinMode(reedPin, INPUT);

  Serial.begin(115200);

  lastReedState = digitalRead(reedPin);

  calibrationStartTime = millis();

  Serial.println("{\"event\":\"photoresistor_calibration_started\",\"duration_seconds\":60}");
}

void loop() {
  checkMagneticSensor();

  if (!calibrated) {
    calibratePhotoresistor();
  } else {
    checkPhotoresistor();
    checkCombinedEvent();
  }

  delay(25);
}

void checkMagneticSensor() {
  int currentReedState = digitalRead(reedPin);

  // Keep this logic unchanged: detects 1 -> 0
  if (lastReedState == HIGH && currentReedState == LOW) {
    lastMagneticEventTime = millis();
    magneticEventActive = true;

    Serial.println("{\"event\":\"magnetic_spring_triggered\",\"sensor\":\"magnetic_spring\",\"value\":0}");
  }

  lastReedState = currentReedState;
}

void calibratePhotoresistor() {
  unsigned long now = millis();

  if (now - lastSampleTime >= sampleIntervalMs) {
    lastSampleTime = now;

    int lightValue = analogRead(photoPin);

    sampleCount++;
    sum += lightValue;
    sumSquares += (double)lightValue * lightValue;
  }

  if (now - calibrationStartTime >= calibrationTimeMs) {
    lightMean = sum / sampleCount;

    double variance = (sumSquares / sampleCount) - (lightMean * lightMean);

    if (variance < 0) {
      variance = 0;
    }

    lightStdDev = sqrt(variance);

    calibrated = true;

    Serial.print("{\"event\":\"photoresistor_calibration_complete\",\"samples\":");
    Serial.print(sampleCount);
    Serial.print(",\"mean\":");
    Serial.print(lightMean, 2);
    Serial.print(",\"stddev\":");
    Serial.print(lightStdDev, 2);
    Serial.println("}");
  }
}

void checkPhotoresistor() {
  int currentLight = analogRead(photoPin);

  double difference = abs(currentLight - lightMean);

  double zScore = 0;
  if (lightStdDev > 0) {
    zScore = difference / lightStdDev;
  }

  if (zScore >= zScoreThreshold && difference >= minRawDifference) {
    lastLightEventTime = millis();
    lightEventActive = true;

    Serial.print("{\"event\":\"significant_light_change\",\"sensor\":\"photoresistor\",\"value\":");
    Serial.print(currentLight);
    Serial.print(",\"mean\":");
    Serial.print(lightMean, 2);
    Serial.print(",\"stddev\":");
    Serial.print(lightStdDev, 2);
    Serial.print(",\"z_score\":");
    Serial.print(zScore, 2);
    Serial.print(",\"difference\":");
    Serial.print(difference, 2);
    Serial.println("}");

    delay(500); // prevents rapid repeated light events
  }
}

void checkCombinedEvent() {
  if (!magneticEventActive || !lightEventActive) {
    return;
  }

  unsigned long timeDifference;

  if (lastMagneticEventTime > lastLightEventTime) {
    timeDifference = lastMagneticEventTime - lastLightEventTime;
  } else {
    timeDifference = lastLightEventTime - lastMagneticEventTime;
  }

  if (timeDifference <= correlationWindowMs) {
    Serial.print("{\"event\":\"intruder_criteria_met\",\"magnetic_sensor\":true,\"light_change\":true,\"time_difference_ms\":");
    Serial.print(timeDifference);
    Serial.println("}");

    magneticEventActive = false;
    lightEventActive = false;
  }

  unsigned long now = millis();

  if (now - lastMagneticEventTime > correlationWindowMs) {
    magneticEventActive = false;
  }

  if (now - lastLightEventTime > correlationWindowMs) {
    lightEventActive = false;
  }
}
