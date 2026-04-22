const int SOUND_D_PIN = 2;
const int SOUND_A_PIN = A1;

void setup() {
  Serial.begin(115200);
  pinMode(SOUND_D_PIN, INPUT);
}

void loop() {
  int d = digitalRead(SOUND_D_PIN);
  int a = analogRead(SOUND_A_PIN);

  Serial.print("D0=");
  Serial.print(d);
  Serial.print("  A0=");
  Serial.println(a);

  delay(50);
}
