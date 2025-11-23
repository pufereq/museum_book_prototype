bool page1Open, page1Close;
bool page2Open, page2Close;
bool page3Open, page3Close;
bool page4Open, page4Close;
bool page5Open, page5Close;

void setup() {
  Serial.begin(9600);

  pinMode(30, INPUT_PULLUP);  // page1Open
  pinMode(31, INPUT_PULLUP);  // page1Close

  pinMode(32, INPUT_PULLUP);  // page2Open
  pinMode(33, INPUT_PULLUP);  // page2Close

  pinMode(34, INPUT_PULLUP);  // page3Open
  pinMode(35, INPUT_PULLUP);  // page3Close
  
  pinMode(36, INPUT_PULLUP);  // page4Open
  pinMode(37, INPUT_PULLUP);  // page4Close

  pinMode(38, INPUT_PULLUP);  // page5Open
  pinMode(39, INPUT_PULLUP);  // page5Close
}

void getPageStatus() {
  page1Open = !digitalRead(30);
  page1Close = !digitalRead(31);

  page2Open = !digitalRead(32);
  page2Close = !digitalRead(33);

  page3Open = !digitalRead(34);
  page3Close = !digitalRead(35);

  page4Open = !digitalRead(36);
  page4Close = !digitalRead(37);

  page5Open = !digitalRead(38);
  page5Close = !digitalRead(39);
}

String CSV() {
  String csv = "";
  csv += String(page1Open) + "," + String(page1Close) + ",";
  csv += String(page2Open) + "," + String(page2Close) + ",";
  csv += String(page3Open) + "," + String(page3Close) + ",";
  csv += String(page4Open) + "," + String(page4Close) + ",";
  csv += String(page5Open) + "," + String(page5Close);
  return csv;
}

void loop() {
  getPageStatus();
  Serial.println(CSV());
  delay(250);
}
