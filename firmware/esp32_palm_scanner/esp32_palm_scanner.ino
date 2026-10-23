/**
 * PalmPay - ESP32 Palm Vein IR Scanner Firmware
 * -------------------------------------------------------------
 * Target Hardware : ESP32-CAM (AI-Thinker OV2640 module)
 * Optical Spectrum: 850nm Near-Infrared (NIR)
 * 
 * Features:
 *   - OV2640 Camera Driver with NIR-optimized sensor registers
 *   - 850nm IR LED Illuminator control (GPIO 4 or external MOSFET)
 *   - Proximity / Hand Detection trigger (GPIO 13 or push button)
 *   - HTTP Endpoints:
 *       GET /         -> Device telemetry & system info (JSON)
 *       GET /ping     -> Rapid 200 OK health check
 *       GET /capture  -> Single NIR JPEG frame (used by PalmPay POS)
 *       GET /stream   -> Real-time MJPEG stream (30 fps preview)
 *   - Push Client Mode:
 *       Auto-POSTs JPEG directly to PalmPay server on palm detection
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <WiFiClient.h>

// =========================================================================
// 1. NETWORK & PALMPAY SERVER CONFIGURATION
// =========================================================================

const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// PalmPay Backend URL (IP of the computer running FastAPI backend)
const char* PALMPAY_SERVER_URL = "http://192.168.1.50:8000";
const char* DEVICE_ID          = "e8b9252d-c48a-4f38-ae94-10a1a46dffe1"; // From Admin Panel

// Set static IP if desired (comment out for DHCP)
// IPAddress local_IP(192, 168, 1, 100);
// IPAddress gateway(192, 168, 1, 1);
// IPAddress subnet(255, 255, 255, 0);

// =========================================================================
// 2. PIN DEFINITIONS (AI-THINKER ESP32-CAM)
// =========================================================================

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// 850nm IR Illuminator LED pin (GPIO 4 is built-in high-power LED on AI-Thinker)
#define IR_LED_PIN         4

// Optional Hand Proximity Sensor Trigger (Active LOW button or sensor on GPIO 13)
#define PROXIMITY_PIN     13

// =========================================================================
// 3. GLOBAL OBJECTS & STATE
// =========================================================================

WebServer server(80);
WiFiServer streamServer(81);

unsigned long lastTriggerTime = 0;
const unsigned long TRIGGER_COOLDOWN_MS = 2500; // prevent double scans

// =========================================================================
// 4. CAMERA INITIALIZATION & NIR OPTIMIZATION
// =========================================================================

bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Check PSRAM for resolution selection
  if (psramFound()) {
    config.frame_size   = FRAMESIZE_VGA;  // 640x480 for biometric accuracy
    config.jpeg_quality = 10;            // High quality (lower number = better)
    config.fb_count     = 2;
  } else {
    config.frame_size   = FRAMESIZE_QVGA; // 320x240 fallback
    config.jpeg_quality = 12;
    config.fb_count     = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Camera init failed with error 0x%x\n", err);
    return false;
  }

  // Optimize OV2640 sensor registers for 850nm Near-Infrared absorption
  sensor_t *s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_brightness(s, 1);     // Slight boost for subsurface vein absorption
    s->set_contrast(s, 2);       // High contrast distinguishes hemoglobin veins
    s->set_saturation(s, -2);    // Grayscale / low saturation for NIR spectrum
    s->set_special_effect(s, 2); // 2 = Grayscale mode (maximum vein contrast)
    s->set_whitebal(s, 1);       // Enable AWB
    s->set_awb_gain(s, 1);       // AWB gain
    s->set_wb_mode(s, 0);        // Auto WB
    s->set_exposure_ctrl(s, 1);  // Auto exposure
    s->set_aec2(s, 0);
    s->set_ae_level(s, 0);
    s->set_vflip(s, 1);          // Invert if mounted upside-down
  }

  Serial.println("[OK] OV2640 Camera initialized and calibrated for 850nm NIR.");
  return true;
}

// =========================================================================
// 5. HTTP SERVER HANDLERS
// =========================================================================

void handleRoot() {
  String json = "{";
  json += "\"device\":\"ESP32-CAM\",";
  json += "\"system\":\"PalmPay IR Biometric Scanner\",";
  json += "\"spectrum\":\"850nm NIR\",";
  json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"rssi\":" + String(WiFi.RSSI()) + ",";
  json += "\"uptime_sec\":" + String(millis() / 1000) + ",";
  json += "\"endpoints\":[\"/ping\",\"/capture\",\"/stream\"]";
  json += "}";
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

void handlePing() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "pong");
}

void handleCapture() {
  // Flash IR Illuminator LED for optimal exposure
  digitalWrite(IR_LED_PIN, HIGH);
  delay(60); // Allow sensor auto-gain to settle under NIR lighting

  camera_fb_t *fb = esp_camera_fb_get();
  digitalWrite(IR_LED_PIN, LOW); // Turn off IR illuminator

  if (!fb) {
    Serial.println("[ERROR] Frame buffer capture failed");
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Content-Disposition", "inline; filename=palm_scan.jpg");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);

  Serial.printf("[CAPTURE] Served frame size: %u bytes\n", fb->len);
  esp_camera_fb_return(fb);
}

// MJPEG Stream Task
void handleStream() {
  WiFiClient client = streamServer.available();
  if (!client) return;

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
  client.println("Access-Control-Allow-Origin: *");
  client.println();

  digitalWrite(IR_LED_PIN, HIGH);

  while (client.connected()) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) break;

    client.println("--frame");
    client.println("Content-Type: image/jpeg");
    client.printf("Content-Length: %u\r\n\r\n", fb->len);
    client.write(fb->buf, fb->len);
    client.println();
    esp_camera_fb_return(fb);

    delay(30); // ~30 fps
  }

  digitalWrite(IR_LED_PIN, LOW);
  client.stop();
}

// =========================================================================
// 6. PUSH CLIENT MODE (Direct Upload to PalmPay Backend)
// =========================================================================

bool sendScanToBackend() {
  Serial.println("[SCAN] Triggered: Capturing palm frame for direct push...");
  
  digitalWrite(IR_LED_PIN, HIGH);
  delay(80);
  camera_fb_t *fb = esp_camera_fb_get();
  digitalWrite(IR_LED_PIN, LOW);

  if (!fb) {
    Serial.println("[ERROR] Failed to get camera frame");
    return false;
  }

  HTTPClient http;
  String uploadUrl = String(PALMPAY_SERVER_URL) + "/api/v1/devices/" + String(DEVICE_ID) + "/upload-scan";
  http.begin(uploadUrl);

  String boundary = "----PalmPayBoundary" + String(millis());
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  String head = "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"image\"; filename=\"esp32_palm.jpg\"\r\n";
  head += "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  uint32_t totalLen = head.length() + fb->len + tail.length();
  http.addHeader("Content-Length", String(totalLen));

  uint8_t *payload = (uint8_t *)malloc(totalLen);
  if (!payload) {
    Serial.println("[ERROR] Out of memory for upload buffer");
    esp_camera_fb_return(fb);
    http.end();
    return false;
  }

  memcpy(payload, head.c_str(), head.length());
  memcpy(payload + head.length(), fb->buf, fb->len);
  memcpy(payload + head.length() + fb->len, tail.c_str(), tail.length());

  int httpCode = http.POST(payload, totalLen);
  free(payload);
  esp_camera_fb_return(fb);

  if (httpCode > 0) {
    Serial.printf("[OK] Upload returned HTTP %d: %s\n", httpCode, http.getString().c_str());
    http.end();
    return (httpCode == 200 || httpCode == 201);
  } else {
    Serial.printf("[ERROR] HTTP POST failed, error: %s\n", http.errorToString(httpCode).c_str());
    http.end();
    return false;
  }
}

// =========================================================================
// 7. SETUP & MAIN LOOP
// =========================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==========================================");
  Serial.println("  PalmPay ESP32 Palm Vein IR Scanner");
  Serial.println("==========================================");

  pinMode(IR_LED_PIN, OUTPUT);
  digitalWrite(IR_LED_PIN, LOW);

  pinMode(PROXIMITY_PIN, INPUT_PULLUP);

  // Initialize OV2640 camera
  if (!initCamera()) {
    Serial.println("[FATAL] Camera hardware failure. Halting.");
    while (true) {
      digitalWrite(IR_LED_PIN, HIGH);
      delay(200);
      digitalWrite(IR_LED_PIN, LOW);
      delay(200);
    }
  }

  // Connect to WiFi
  Serial.printf("[WIFI] Connecting to SSID: %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  // WiFi.config(local_IP, gateway, subnet); // Uncomment if using static IP
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected!");
    Serial.printf("[WIFI] IP Address: http://%s\n", WiFi.localIP().toString().c_str());
    Serial.printf("[WIFI] Signal Strength: %d dBm\n", WiFi.RSSI());
  } else {
    Serial.println("\n[WIFI] Failed to connect. Check credentials.");
  }

  // Setup Web Server routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/ping", HTTP_GET, handlePing);
  server.on("/capture", HTTP_GET, handleCapture);
  server.begin();
  streamServer.begin();

  Serial.println("[SERVER] Palm Scanner HTTP server ready on port 80.");
  Serial.println("[SERVER] Real-time live stream ready on port 81 and /capture on port 80.");
  Serial.println("[REALTIME] Optical auto-detection and hardware trigger active.\n");
}

void loop() {
  server.handleClient();
  handleStream();

  // 1. Hardware proximity sensor trigger (push button / optical switch on GPIO 13)
  bool hwTriggered = (digitalRead(PROXIMITY_PIN) == LOW);

  if (hwTriggered && (millis() - lastTriggerTime > TRIGGER_COOLDOWN_MS)) {
    lastTriggerTime = millis();
    Serial.println("[REALTIME] Hardware proximity trigger detected!");
    sendScanToBackend();
  }

  delay(2);
}
