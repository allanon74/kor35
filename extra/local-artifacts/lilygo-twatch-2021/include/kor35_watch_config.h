#pragma once

/*
  Configurazione locale T-Watch per KOR35.
  Questo file resta in area local-artifacts (non deployata).
*/

// Wi-Fi locale usato durante evento (hotspot edge) o test.
static const char *KOR35_WIFI_SSID = "KOR35_EDGE_WIFI";
static const char *KOR35_WIFI_PASSWORD = "CAMBIAMI_SUBITO";

// Endpoint API base (nessuna credenziale hardcoded qui).
// Esempio edge in bosco: http://10.42.0.1
// Esempio casa/lab:      http://192.168.1.50
static const char *KOR35_API_BASE_URL = "http://10.42.0.1";

// Endpoint di health/readiness lato backend KOR35.
static const char *KOR35_API_HEALTH_PATH = "/api/health/";
static const char *KOR35_API_WATCH_PAIR_START_PATH = "/api/personaggi/api/device/watch/pair/start/";
static const char *KOR35_API_WATCH_PROFILE_PATH = "/api/personaggi/api/device/watch/profile/";
static const char *KOR35_API_WATCH_SYNC_PATH = "/api/personaggi/api/device/watch/sync/";
static const char *KOR35_API_WATCH_OTA_MANIFEST_PATH = "/api/personaggi/api/device/watch/ota/manifest/";
static const char *KOR35_FIRMWARE_VERSION = "0.1.0";

// Identificativo dispositivo (seriale logico nel sistema gioco).
static const char *KOR35_DEVICE_ID = "twatch-2021-alpha-01";

// Intervallo polling API (ms).
static const uint32_t KOR35_API_POLL_MS = 5000;
static const uint32_t KOR35_CLOCK_REFRESH_MS = 1000;
static const uint32_t KOR35_OTA_CHECK_MS = 120000;
static const size_t KOR35_EVENT_QUEUE_MAX = 32;
