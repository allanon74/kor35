#include <Arduino.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>
#include <WiFi.h>
#include <Wire.h>

#include <ArduinoJson.h>
#include <TTGO.h>

#include "kor35_watch_config.h"

TTGOClass *watch = nullptr;
bool wifiConnected = false;
unsigned long lastPollMs = 0;
unsigned long lastClockRefreshMs = 0;
unsigned long lastOtaCheckMs = 0;
String lastIp = "-";
String pairingCode = "";
String pairToken = "";
String pgName = "-";
int pvCur = 0, paCur = 0, psCur = 0, chaCur = 0;
int pvMax = 0, paMax = 0, psMax = 0, chaMax = 0;
uint16_t pvColor = TFT_RED;
uint16_t paColor = TFT_GREEN;
uint16_t psColor = TFT_MAGENTA;
uint16_t chaColor = TFT_CYAN;
String timerLine = "Nessun timer";
uint8_t screenIndex = 0;
int highlightedGameRow = -1;
unsigned long highlightUntilMs = 0;
unsigned long lastAcceptedTouchMs = 0;
String lastDeltaLabel = "";

static const unsigned long TOUCH_DEBOUNCE_MS = 250;
static const unsigned long TOUCH_HIGHLIGHT_MS = 500;

struct StatEvent {
  String clientEventId;
  String statSigla;
  int delta;
};
StatEvent eventQueue[KOR35_EVENT_QUEUE_MAX];
size_t queueCount = 0;

static String composeUrl(const char *path) {
  String url = String(KOR35_API_BASE_URL);
  url += String(path);
  return url;
}

static uint16_t parseHexColorTo565(const char *hexColor, uint16_t fallbackColor) {
  if (!hexColor) return fallbackColor;
  String raw = String(hexColor);
  raw.trim();
  if (raw.length() == 0) return fallbackColor;
  if (raw.charAt(0) == '#') raw.remove(0, 1);
  if (raw.length() != 6) return fallbackColor;

  char *endPtr = nullptr;
  const long v = strtol(raw.c_str(), &endPtr, 16);
  if (!endPtr || *endPtr != '\0') return fallbackColor;
  const uint8_t r = (uint8_t)((v >> 16) & 0xFF);
  const uint8_t g = (uint8_t)((v >> 8) & 0xFF);
  const uint8_t b = (uint8_t)(v & 0xFF);
  return watch->tft->color565(r, g, b);
}

static void drawGameRow(int rowIndex, int y, const char *label, int cur, int maxv) {
  if (!watch) return;
  uint16_t rowColor = TFT_WHITE;
  if (rowIndex == 0) rowColor = pvColor;
  else if (rowIndex == 1) rowColor = paColor;
  else if (rowIndex == 2) rowColor = psColor;
  else if (rowIndex == 3) rowColor = chaColor;

  const bool isHighlighted = (rowIndex == highlightedGameRow) && (millis() < highlightUntilMs);
  if (isHighlighted) {
    watch->tft->fillRoundRect(4, y - 2, 230, 14, 3, TFT_DARKGREY);
    watch->tft->setTextColor(rowColor, TFT_DARKGREY);
  } else {
    watch->tft->setTextColor(rowColor, TFT_BLACK);
  }
  watch->tft->setCursor(8, y);
  watch->tft->printf("%s %d/%d", label, cur, maxv);
  if (isHighlighted && lastDeltaLabel.length() > 0) {
    watch->tft->setCursor(178, y);
    watch->tft->print(lastDeltaLabel);
  }
}

static void drawClockHeader() {
  if (!watch) return;
  watch->tft->setTextColor(TFT_CYAN, TFT_BLACK);
  watch->tft->setTextSize(2);
  watch->tft->setCursor(8, 6);
  const uint32_t sec = millis() / 1000U;
  const uint32_t hh = (sec / 3600U) % 24U;
  const uint32_t mm = (sec / 60U) % 60U;
  const uint32_t ss = sec % 60U;
  char clockBuf[16];
  snprintf(clockBuf, sizeof(clockBuf), "%02lu:%02lu:%02lu", (unsigned long)hh, (unsigned long)mm, (unsigned long)ss);
  watch->tft->println(clockBuf);
}

static void drawScreen() {
  if (!watch) return;
  watch->tft->fillScreen(TFT_BLACK);
  drawClockHeader();
  watch->tft->setTextSize(1);
  watch->tft->setTextColor(TFT_WHITE, TFT_BLACK);
  if (screenIndex == 0) {
    watch->tft->setCursor(8, 36);
    watch->tft->println("KOR35 Watch");
    watch->tft->setCursor(8, 52);
    watch->tft->println(wifiConnected ? "Connesso Wi-Fi" : "Disconnesso");
    watch->tft->setCursor(8, 68);
    watch->tft->println("Tap sx: Connetti");
    watch->tft->setCursor(8, 84);
    watch->tft->println("Tap dx: Schermata successiva");
    if (pairingCode.length() > 0) {
      watch->tft->setTextColor(TFT_YELLOW, TFT_BLACK);
      watch->tft->setCursor(8, 106);
      watch->tft->printf("Code: %s", pairingCode.c_str());
    }
  } else if (screenIndex == 1) {
    watch->tft->setCursor(8, 36);
    watch->tft->printf("PG: %s", pgName.c_str());
    watch->tft->setCursor(8, 52);
    watch->tft->printf("IP: %s", lastIp.c_str());
    watch->tft->setCursor(8, 68);
    watch->tft->printf("Pair: %s", pairToken.length() > 0 ? "OK" : "NO");
  } else if (screenIndex == 2) {
    drawGameRow(0, 36, "PV", pvCur, pvMax);
    drawGameRow(1, 52, "PA", paCur, paMax);
    drawGameRow(2, 68, "PG", psCur, psMax);
    drawGameRow(3, 84, "CHA", chaCur, chaMax);
    watch->tft->setTextColor(TFT_WHITE, TFT_BLACK);
    watch->tft->setCursor(8, 106);
    watch->tft->println("Tap riga:-1  Long press riga:+1");
  } else {
    watch->tft->setCursor(8, 36);
    watch->tft->println("Timers attivi");
    watch->tft->setCursor(8, 52);
    watch->tft->println(timerLine);
  }
}

static bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(KOR35_WIFI_SSID, KOR35_WIFI_PASSWORD);
  const unsigned long startMs = millis();

  while (WiFi.status() != WL_CONNECTED && (millis() - startMs) < 15000) {
    delay(300);
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    lastIp = WiFi.localIP().toString();
    Serial.printf("Wi-Fi connesso. IP: %s\n", lastIp.c_str());
    return true;
  }
  wifiConnected = false;
  Serial.println("Wi-Fi non connesso.");
  return false;
}

static void queueEvent(const String &sigla, int delta) {
  if (queueCount >= KOR35_EVENT_QUEUE_MAX) return;
  StatEvent ev;
  ev.clientEventId = String(KOR35_DEVICE_ID) + "-" + String(millis());
  ev.statSigla = sigla;
  ev.delta = delta;
  eventQueue[queueCount++] = ev;
}

static void applyStatDelta(const String &sigla, int delta) {
  if (delta == 0) return;
  if (sigla == "PV") {
    pvCur = max(0, min(pvMax, pvCur + delta));
  } else if (sigla == "PA") {
    paCur = max(0, min(paMax, paCur + delta));
  } else if (sigla == "PS") {
    psCur = max(0, min(psMax, psCur + delta));
  } else if (sigla == "CHA") {
    chaCur = max(0, min(chaMax, chaCur + delta));
  } else {
    return;
  }
  queueEvent(sigla, delta);
}

static bool pairStart() {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(composeUrl(KOR35_API_WATCH_PAIR_START_PATH));
  http.setTimeout(3000);
  http.addHeader("Content-Type", "application/json");
  StaticJsonDocument<128> req;
  req["device_id"] = KOR35_DEVICE_ID;
  String body;
  serializeJson(req, body);
  int code = http.POST(body);
  if (code <= 0) {
    http.end();
    return false;
  }
  String response = http.getString();
  http.end();
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, response)) return false;
  pairingCode = String((const char *)doc["pairing_code"]);
  return pairingCode.length() > 0;
}

static void parseProfile(const String &response) {
  StaticJsonDocument<4096> doc;
  if (deserializeJson(doc, response)) return;
  JsonObject pg = doc["personaggio"];
  if (!pg.isNull()) {
    pgName = String((const char *)pg["nome"]);
    JsonArray stats = pg["risorse_pool_ui"].as<JsonArray>();
    for (JsonVariant v : stats) {
      const char *sigla = v["sigla"] | "";
      int cur = v["valore_corrente"] | 0;
      int maxv = v["valore_max"] | 0;
      const char *colorHex = v["colore"] | "";
      if (strcmp(sigla, "PV") == 0) { pvCur = cur; pvMax = maxv; }
      if (strcmp(sigla, "PA") == 0) { paCur = cur; paMax = maxv; }
      if (strcmp(sigla, "PS") == 0) { psCur = cur; psMax = maxv; }
      if (strcmp(sigla, "CHA") == 0) { chaCur = cur; chaMax = maxv; }
      if (strcmp(sigla, "PV") == 0) pvColor = parseHexColorTo565(colorHex, pvColor);
      if (strcmp(sigla, "PA") == 0) paColor = parseHexColorTo565(colorHex, paColor);
      if (strcmp(sigla, "PS") == 0) psColor = parseHexColorTo565(colorHex, psColor);
      if (strcmp(sigla, "CHA") == 0) chaColor = parseHexColorTo565(colorHex, chaColor);
    }
    JsonArray timers = doc["timers"].as<JsonArray>();
    if (!timers.isNull() && timers.size() > 0) {
      const char *name = timers[0]["nome"] | "Timer";
      timerLine = String(name);
    } else {
      timerLine = "Nessun timer";
    }
  }
}

static bool fetchProfile() {
  if (WiFi.status() != WL_CONNECTED || pairToken.length() == 0) return false;
  HTTPClient http;
  const String url = composeUrl(KOR35_API_WATCH_PROFILE_PATH) + "?device_id=" + String(KOR35_DEVICE_ID);
  http.begin(url);
  http.setTimeout(3000);
  http.addHeader("X-KOR35-Pair-Token", pairToken);
  const int code = http.GET();
  if (code <= 0) {
    http.end();
    return false;
  }
  parseProfile(http.getString());
  http.end();
  return true;
}

static bool flushQueue() {
  if (queueCount == 0 || WiFi.status() != WL_CONNECTED || pairToken.length() == 0) return false;
  HTTPClient http;
  http.begin(composeUrl(KOR35_API_WATCH_SYNC_PATH));
  http.setTimeout(4000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-KOR35-Pair-Token", pairToken);
  StaticJsonDocument<4096> req;
  req["device_id"] = KOR35_DEVICE_ID;
  JsonArray events = req.createNestedArray("events");
  for (size_t i = 0; i < queueCount; i++) {
    JsonObject e = events.createNestedObject();
    e["client_event_id"] = eventQueue[i].clientEventId;
    e["stat_sigla"] = eventQueue[i].statSigla;
    e["delta"] = eventQueue[i].delta;
  }
  String body;
  serializeJson(req, body);
  int code = http.POST(body);
  if (code > 0) {
    String response = http.getString();
    parseProfile(response);
    queueCount = 0;
    http.end();
    return true;
  }
  http.end();
  return false;
}

static bool isVersionNewer(const String &remoteVersion) {
  int lMaj = 0, lMin = 0, lPat = 0;
  int rMaj = 0, rMin = 0, rPat = 0;
  sscanf(KOR35_FIRMWARE_VERSION, "%d.%d.%d", &lMaj, &lMin, &lPat);
  sscanf(remoteVersion.c_str(), "%d.%d.%d", &rMaj, &rMin, &rPat);
  if (rMaj != lMaj) return rMaj > lMaj;
  if (rMin != lMin) return rMin > lMin;
  return rPat > lPat;
}

static void checkOtaUpdate() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(composeUrl(KOR35_API_WATCH_OTA_MANIFEST_PATH));
  http.setTimeout(4000);
  int code = http.GET();
  if (code <= 0) {
    http.end();
    return;
  }
  String response = http.getString();
  http.end();

  StaticJsonDocument<512> doc;
  if (deserializeJson(doc, response)) return;
  const bool enabled = doc["enabled"] | false;
  const String remoteVersion = String((const char *)doc["version"]);
  const String firmwareUrl = String((const char *)doc["firmware_url"]);
  if (!enabled || remoteVersion.length() == 0 || firmwareUrl.length() == 0) return;
  if (!isVersionNewer(remoteVersion)) return;

  drawScreen();
  watch->tft->setTextColor(TFT_YELLOW, TFT_BLACK);
  watch->tft->setCursor(8, 122);
  watch->tft->println("OTA update...");
  t_httpUpdate_return ret = httpUpdate.update(firmwareUrl);
  switch (ret) {
    case HTTP_UPDATE_FAILED:
      Serial.printf("OTA failed (%d): %s\n", httpUpdate.getLastError(), httpUpdate.getLastErrorString().c_str());
      break;
    case HTTP_UPDATE_NO_UPDATES:
      Serial.println("OTA: no updates");
      break;
    case HTTP_UPDATE_OK:
      Serial.println("OTA: updated, rebooting");
      break;
  }
}

static void handleTouch() {
  if (!watch) return;
  int16_t x = 0, y = 0;
  if (!watch->getTouch(x, y)) return;
  const unsigned long nowMs = millis();
  if (nowMs - lastAcceptedTouchMs < TOUCH_DEBOUNCE_MS) return;

  const unsigned long touchStart = millis();
  while (watch->getTouch(x, y)) {
    delay(20);
    if (millis() - touchStart > 1200) break;
  }
  const bool isLongPress = (millis() - touchStart) >= 500;
  if (screenIndex == 0 && x < 120) {
    lastAcceptedTouchMs = nowMs;
    connectWifi();
    if (wifiConnected) pairStart();
    drawScreen();
    delay(250);
    return;
  }
  if (screenIndex == 2) {
    String targetSigla = "CHA";
    int rowIndex = 3;
    if (y < 44) targetSigla = "PV";
    if (y < 44) rowIndex = 0;
    else if (y < 60) {
      targetSigla = "PA";
      rowIndex = 1;
    } else if (y < 76) {
      targetSigla = "PS";
      rowIndex = 2;
    } else {
      targetSigla = "CHA";
      rowIndex = 3;
    }

    const int delta = isLongPress ? +1 : -1;
    lastAcceptedTouchMs = nowMs;
    highlightedGameRow = rowIndex;
    highlightUntilMs = millis() + TOUCH_HIGHLIGHT_MS;
    lastDeltaLabel = delta > 0 ? "+1" : "-1";
    applyStatDelta(targetSigla, delta);
    drawScreen();
    delay(220);
    return;
  }
  lastAcceptedTouchMs = nowMs;
  screenIndex = (screenIndex + 1) % 4;
  drawScreen();
  delay(220);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  watch = TTGOClass::getWatch();
  watch->begin();
  watch->openBL();
  watch->tft->setRotation(1);
  drawScreen();
  connectWifi();
  pairStart();
  lastPollMs = millis();
  lastClockRefreshMs = millis();
  lastOtaCheckMs = millis();
}

void loop() {
  handleTouch();
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnected = false;
    connectWifi();
  }

  if (millis() - lastClockRefreshMs >= KOR35_CLOCK_REFRESH_MS) {
    drawScreen();
    lastClockRefreshMs = millis();
  }

  if (millis() - lastPollMs >= KOR35_API_POLL_MS) {
    flushQueue();
    fetchProfile();
    lastPollMs = millis();
  }

  if (millis() - lastOtaCheckMs >= KOR35_OTA_CHECK_MS) {
    checkOtaUpdate();
    lastOtaCheckMs = millis();
  }

  delay(50);
}
