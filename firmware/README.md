# ESP32 Palm Vein Near-Infrared (NIR) Scanner Hardware & Firmware

This directory contains the firmware and hardware assembly guide for the **PalmPay Contactless Palm-Vein Biometric Terminal**.

---

## 1. Operating Principle

Palm vein authentication works on the optical absorption characteristics of blood:
- **Deoxygenated hemoglobin** in subcutaneous veins strongly absorbs near-infrared light at **850 nm** (and 940 nm).
- The surrounding superficial tissue, fat, and skin reflect the infrared radiation.
- An infrared camera sensor captures this subsurface contrast as an intricate network of dark lines (the vascular palm pattern), which is impossible to forge using photograph printouts or standard RGB cameras.

```
       [ 850nm NIR LEDs ] ───▶ Subsurface Vein Absorption
              │
              ▼
   [ Palm Vascular Network ]
              │
              ▼
    [ OV2640 NIR Camera ] ──(No IR Cut Filter)
              │
              ▼
     [ ESP32 Controller ] ──▶ WiFi (HTTP / MJPEG)
              │
              ▼
   [ PalmPay FastAPI Backend ] (512-D AI Embeddings + pgvector)
```

---

## 2. Hardware Bill of Materials (BOM)

| Component | Recommended Model | Notes |
|---|---|---|
| **Microcontroller** | ESP32-CAM (AI-Thinker) | Includes 4MB PSRAM, WiFi, microSD slot |
| **Camera Sensor** | OV2640 with **NO IR Filter** | **Critical**: Standard OV2640 filters out IR light. Use an OV2640 lens without an IR cut filter (e.g., "Night Vision" / "NoIR" lens) |
| **Infrared Illuminator** | 850nm NIR LED Ring / Module | 6 to 12 LEDs (850nm), with current-limiting resistor or MOSFET switch |
| **Proximity Sensor** | VL53L0X ToF / IR proximity switch | Connected to GPIO 13 (active LOW) for auto-detect when a palm approaches within 5–15 cm |
| **Power Supply** | 5V 2A DC Supply | ESP32-CAM draws high current bursts during WiFi transmission & camera capture |
| **USB to TTL Adapter** | FTDI FT232RL or CP2102 | For flashing code via UART (GPIO 1 TX, GPIO 3 RX, IO0 to GND) |

---

## 3. Wiring Diagram

```
ESP32-CAM Pin     Peripheral / Connection
─────────────     ──────────────────────────────────────────────────
5V            ──▶ +5V Power Supply (2A)
GND           ──▶ Common GND
GPIO 4        ──▶ IR LED Illuminator (or MOSFET Gate driving 850nm LED ring)
GPIO 13       ──▶ Proximity Sensor Trigger / Hand Detect (Active LOW)
U0R (GPIO 3)  ──▶ FTDI Programmer TX (Flashing only)
U0T (GPIO 1)  ──▶ FTDI Programmer RX (Flashing only)
IO0           ──▶ Connect to GND during flashing; disconnect for boot
```

---

## 4. Flashing Instructions (Arduino IDE)

1. **Install ESP32 Board Package**:
   - In Arduino IDE, open **Preferences** and add to Additional Boards Manager URLs:
     `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Open **Tools > Board > Boards Manager**, search for `esp32` by Espressif Systems and click **Install**.

2. **Select Board Settings**:
   - **Board**: `AI Thinker ESP32-CAM`
   - **CPU Frequency**: `240MHz (WiFi/BT)`
   - **Flash Frequency**: `80MHz`
   - **Flash Mode**: `QIO`
   - **Partition Scheme**: `Huge APP (3MB No OTA/1MB SPIFFS)`
   - **PSRAM**: `Enabled`

3. **Configure Network & Device**:
   - Open `esp32_palm_scanner.ino`.
   - Update `WIFI_SSID` and `WIFI_PASSWORD` with your local 2.4 GHz network credentials.
   - Update `PALMPAY_SERVER_URL` with your server IP (e.g., `http://192.168.1.50:8000`).
   - Update `DEVICE_ID` with the registered device UUID from the PalmPay Admin tab.

4. **Flash**:
   - Connect **IO0 to GND**.
   - Press the ESP32 **RST** button to enter bootloader mode.
   - Click **Upload** in Arduino IDE.
   - Once upload completes, disconnect **IO0 from GND** and press **RST**.

---

## 5. Network Endpoints & POS Integration

Once connected to WiFi, the ESP32 prints its local IP address over the Serial Monitor (115200 baud).

### Endpoints exposed by ESP32:
- `GET /` — Returns device telemetry JSON (IP, signal RSSI, uptime, spectrum specs).
- `GET /ping` — Returns `pong` (200 OK) for latency testing.
- `GET /capture` — Triggers 850nm IR illumination, captures high-contrast frame, and returns a binary JPEG image.
- `GET /stream` — Continuous MJPEG video feed (port 81) for live HUD preview.

### Using in PalmPay Web Terminal:
1. In the PalmPay POS view, select **ESP32 Device** as the scanner source.
2. Enter the ESP32 IP address (e.g., `http://192.168.1.100`) in the endpoint bar.
3. Click **Test Ping** to confirm communication (green badge will indicate `ESP32 READY`).
4. Click **Scan with ESP32 Device** or toggle **ESP32 Auto-Poll: ON** to process payments automatically when a customer presents their palm!
