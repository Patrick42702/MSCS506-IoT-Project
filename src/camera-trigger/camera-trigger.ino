/*
  Doorway Suspicion Scoring Demo
  - Photoresistor on PHOTO_PIN (analog)
  - Sound sensor analog on SOUND_A_PIN
  - Sound sensor digital on SOUND_D_PIN
  - Serial JSON output at 115200

  Behavior:
  - Maintain light + sound baselines when idle
  - Start a 2-second event window when sound/light becomes suspicious
  - Score the window
  - Publish one JSON event
  - Enter cooldown to prevent repeat triggers
*/

const int PHOTO_PIN    = A0;
const int SOUND_A_PIN  = A1;
const int SOUND_D_PIN  = 2;

// ---------- timing ----------
const unsigned long SAMPLE_MS        = 50;     // main loop sample period
const unsigned long EVENT_WINDOW_MS  = 2000;   // evidence collection window
const unsigned long COOLDOWN_MS      = 10000;  // ignore retriggers for 10 sec
const unsigned long SPIKE_GAP_MS     = 180;    // debounce/refractory for sound spikes

// ---------- baseline smoothing ----------
// Smaller alpha = slower baseline update
const float LIGHT_BASELINE_ALPHA = 0.02f;
const float SOUND_BASELINE_ALPHA = 0.05f;

// ---------- light thresholds ----------
// Relative thresholds are better than fixed raw ADC values
const float LIGHT_MOD_FRAC   = 0.12f;  // 12% above baseline
const float LIGHT_STRONG_FRAC= 0.25f;  // 25% above baseline
const float LIGHT_RATE_FRAC  = 0.08f;  // fast rise = 8% baseline in one sample

// ---------- sound thresholds ----------
// Analog values are only supportive; D0 is the main spike detector
const int SOUND_A_MOD_DELTA    = 60;
const int SOUND_A_STRONG_DELTA = 120;

// ---------- score thresholds ----------
const int SCORE_SUSPICIOUS = 4;
const int SCORE_HIGH       = 7;

// ---------- state ----------
float lightBaseline = 0.0f;
float soundBaseline = 0.0f;
int prevLight = 0;
bool baselinesInitialized = false;

bool eventActive = false;
unsigned long eventStartMs = 0;
unsigned long cooldownUntilMs = 0;

// ---------- event features ----------
int startLight = 0;
int maxLight = 0;
int maxLightDelta = 0;
int maxLightRate = 0;
bool lightDetected = false;
bool fastLightRise = false;
unsigned long firstLightMs = 0;

int maxSoundA = 0;
int maxSoundADelta = 0;
int soundSpikeCount = 0;
bool soundDetected = false;
unsigned long firstSoundMs = 0;
unsigned long lastSpikeMs = 0;

// Track D0 edges
bool prevSoundDigitalActive = false;

// ---------- helper ----------
float expSmooth(float baseline, float value, float alpha) {
  return baseline + alpha * (value - baseline);
}

void resetEventFeatures() {
  startLight = 0;
  maxLight = 0;
  maxLightDelta = 0;
  maxLightRate = 0;
  lightDetected = false;
  fastLightRise = false;
  firstLightMs = 0;

  maxSoundA = 0;
  maxSoundADelta = 0;
  soundSpikeCount = 0;
  soundDetected = false;
  firstSoundMs = 0;
  lastSpikeMs = 0;
}

void beginEventWindow(int lightRaw, int soundRawA, unsigned long nowMs) {
  eventActive = true;
  eventStartMs = nowMs;
  resetEventFeatures();

  startLight = lightRaw;
  maxLight = lightRaw;
  maxSoundA = soundRawA;
}

int computeScore() {
  int score = 0;

  // Sound analog contribution
  if (maxSoundADelta > SOUND_A_STRONG_DELTA) {
    score += 4;
  } else if (maxSoundADelta > SOUND_A_MOD_DELTA) {
    score += 2;
  }

  // Sound repeated spikes
  if (soundSpikeCount >= 2) {
    score += 2;
  } else if (soundSpikeCount == 1) {
    score += 1;
  }

  // Light contribution
  float lightModThresh    = lightBaseline * LIGHT_MOD_FRAC;
  float lightStrongThresh = lightBaseline * LIGHT_STRONG_FRAC;

  if (maxLightDelta > (int)lightStrongThresh) {
    score += 3;
  } else if (maxLightDelta > (int)lightModThresh) {
    score += 2;
  }

  if (fastLightRise) {
    score += 1;
  }

  // Correlation bonus
  if (soundDetected && lightDetected) {
    unsigned long dt = (firstSoundMs > firstLightMs)
      ? (firstSoundMs - firstLightMs)
      : (firstLightMs - firstSoundMs);

    if (dt <= 1000) {
      score += 3;
    }
  }

  return score;
}

const char* classifyEvent(int score) {
  if (score >= SCORE_HIGH) return "high_suspicion";
  if (score >= SCORE_SUSPICIOUS) return "suspicious";
  return "ignore";
}

void emitJsonEvent(unsigned long nowMs, int lightRaw, int soundRawA, int score, const char* eventType) {
  Serial.print("{");
  Serial.print("\"ts_ms\":"); Serial.print(nowMs);

  Serial.print(",\"light_raw\":"); Serial.print(lightRaw);
  Serial.print(",\"light_baseline\":"); Serial.print((int)lightBaseline);
  Serial.print(",\"max_light_delta\":"); Serial.print(maxLightDelta);
  Serial.print(",\"max_light_rate\":"); Serial.print(maxLightRate);

  Serial.print(",\"sound_a_raw\":"); Serial.print(soundRawA);
  Serial.print(",\"sound_a_baseline\":"); Serial.print((int)soundBaseline);
  Serial.print(",\"max_sound_a_delta\":"); Serial.print(maxSoundADelta);
  Serial.print(",\"sound_spike_count\":"); Serial.print(soundSpikeCount);

  Serial.print(",\"light_detected\":"); Serial.print(lightDetected ? "true" : "false");
  Serial.print(",\"sound_detected\":"); Serial.print(soundDetected ? "true" : "false");
  Serial.print(",\"fast_light_rise\":"); Serial.print(fastLightRise ? "true" : "false");

  Serial.print(",\"score\":"); Serial.print(score);
  Serial.print(",\"event_type\":\""); Serial.print(eventType); Serial.print("\"");
  Serial.println("}");
}

void setup() {
  Serial.begin(115200);

  pinMode(SOUND_D_PIN, INPUT); // use INPUT_PULLUP only if your module/output wiring needs it
  // pinMode(SOUND_D_PIN, INPUT_PULLUP);

  // Warm-up baseline
  long sumLight = 0;
  long sumSound = 0;
  const int warmupSamples = 40;

  for (int i = 0; i < warmupSamples; i++) {
    sumLight += analogRead(PHOTO_PIN);
    sumSound += analogRead(SOUND_A_PIN);
    delay(20);
  }

  lightBaseline = sumLight / (float)warmupSamples;
  soundBaseline = sumSound / (float)warmupSamples;
  prevLight = (int)lightBaseline;
  baselinesInitialized = true;

  Serial.println("{\"status\":\"ready\"}");
}

void loop() {
  static unsigned long lastSampleMs = 0;
  unsigned long nowMs = millis();

  if (nowMs - lastSampleMs < SAMPLE_MS) return;
  lastSampleMs = nowMs;

  // ----- read sensors -----
  int lightRaw = analogRead(PHOTO_PIN);
  int soundRawA = analogRead(SOUND_A_PIN);

  // Many LM393 sound boards are active LOW on D0 when threshold exceeded.
  bool soundDigitalActive = (digitalRead(SOUND_D_PIN) == LOW);

  if (!baselinesInitialized) return;

  // ----- cooldown -----
  bool inCooldown = (nowMs < cooldownUntilMs);

  // ----- update baselines only when idle -----
  if (!eventActive && !inCooldown) {
    lightBaseline = expSmooth(lightBaseline, lightRaw, LIGHT_BASELINE_ALPHA);
    soundBaseline = expSmooth(soundBaseline, soundRawA, SOUND_BASELINE_ALPHA);
  }

  // ----- current derived features -----
  int lightDelta = lightRaw - (int)lightBaseline;
  int lightRate = lightRaw - prevLight;
  prevLight = lightRaw;

  int soundADelta = soundRawA - (int)soundBaseline;

  int lightModThresh    = (int)(lightBaseline * LIGHT_MOD_FRAC);
  int lightStrongThresh = (int)(lightBaseline * LIGHT_STRONG_FRAC);
  int lightRateThresh   = (int)(lightBaseline * LIGHT_RATE_FRAC);

  bool lightModerate = (lightDelta > lightModThresh);
  bool lightStrong   = (lightDelta > lightStrongThresh);
  bool lightFast     = (lightRate > lightRateThresh);

  bool soundAnalogModerate = (soundADelta > SOUND_A_MOD_DELTA);
  bool soundAnalogStrong   = (soundADelta > SOUND_A_STRONG_DELTA);

  // ----- event start condition -----
  bool startCondition =
      lightModerate ||
      soundDigitalActive ||
      soundAnalogModerate;

  if (!eventActive && !inCooldown && startCondition) {
    beginEventWindow(lightRaw, soundRawA, nowMs);
  }

  // ----- accumulate event evidence -----
  if (eventActive) {
    // Track max light
    if (lightRaw > maxLight) maxLight = lightRaw;
    if (lightDelta > maxLightDelta) maxLightDelta = lightDelta;
    if (lightRate > maxLightRate) maxLightRate = lightRate;

    // Light flags
    if (!lightDetected && (lightModerate || lightStrong)) {
      lightDetected = true;
      firstLightMs = nowMs;
    }
    if (lightFast) {
      fastLightRise = true;
    }

    // Track max sound analog
    if (soundRawA > maxSoundA) maxSoundA = soundRawA;
    if (soundADelta > maxSoundADelta) maxSoundADelta = soundADelta;

    // Count digital sound spikes by edge + refractory period
    bool risingSoundEvent = (soundDigitalActive && !prevSoundDigitalActive);

    if (risingSoundEvent && (nowMs - lastSpikeMs >= SPIKE_GAP_MS)) {
      soundSpikeCount++;
      lastSpikeMs = nowMs;

      if (!soundDetected) {
        soundDetected = true;
        firstSoundMs = nowMs;
      }
    }

    // If D0 never triggers but analog sound is strong, still mark sound detected
    if (!soundDetected && (soundAnalogModerate || soundAnalogStrong)) {
      soundDetected = true;
      firstSoundMs = nowMs;
    }

    // End window
    if (nowMs - eventStartMs >= EVENT_WINDOW_MS) {
      int score = computeScore();
      const char* eventType = classifyEvent(score);

      emitJsonEvent(nowMs, lightRaw, soundRawA, score, eventType);

      eventActive = false;
      cooldownUntilMs = nowMs + COOLDOWN_MS;
    }
  }

  prevSoundDigitalActive = soundDigitalActive;
}
