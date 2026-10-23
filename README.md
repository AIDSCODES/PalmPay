# PalmPay - Contactless Palm-Vein Biometric Payment System

PalmPay is a biometric payment and point-of-sale (POS) terminal system that identifies customers and authorizes transactions using subsurface palm-vein vascular patterns captured under near-infrared (850nm NIR) illumination.

---

## Architecture Overview

```
 [ Customer Palm ]
         │
         ▼ (850nm NIR Absorption)
 [ ESP32-CAM + OV2640 (NoIR) ] ── (WiFi / HTTP) ──▶ [ PalmPay POS Terminal (Frontend) ]
                                                              │
                                                              ▼
                                                   [ FastAPI Backend ]
                                                              │
                                                              ▼
                                                  [ AI 512-D Embedding Model ]
                                                              │
                                                              ▼
                                              [ pgvector Similarity Search (HNSW) ]
                                                              │
                                                              ▼
                                                 [ User Wallet & Payment Ledger ]
```

---

## Repository Structure

- **[`firmware/`](file:///d:/iot/firmware)**:
  - [`esp32_palm_scanner.ino`](file:///d:/iot/firmware/esp32_palm_scanner/esp32_palm_scanner.ino): Production-ready Arduino C++ firmware for the AI-Thinker ESP32-CAM module.
  - Controls 850nm IR LEDs, exposes `/capture`, `/stream`, `/ping` HTTP endpoints, and supports direct push upload to the backend.
  - [`firmware/README.md`](file:///d:/iot/firmware/README.md): Hardware Bill of Materials (BOM), optical physics, wiring pinouts, and flashing instructions.

- **[`backend/`](file:///d:/iot/backend)**:
  - FastAPI asynchronous backend service.
  - Real-time palm-vein biometric feature extraction (512-dimensional vector embedding).
  - PostgreSQL with `pgvector` HNSW index for sub-millisecond 1:N similarity search.
  - Atomic wallet balances, transaction ledgers, device HMAC authentication, and idempotency protection.

- **[`frontend/`](file:///d:/iot/frontend)**:
  - Cyber-tactical POS terminal HUD with audio feedback.
  - Interactive ESP32 hardware device management (IP configuration, live ping status, auto-polling).
  - Real-time ESP32 live MJPEG stream HUD and continuous palm auto-matching.

---

## Quick Start

### 1. Start the Backend
```bash
cd backend
# With Docker:
docker-compose up -d

# Or locally:
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Launch the POS Frontend
Open `frontend/index.html` in any modern web browser or serve it with any local static HTTP server:
```bash
cd frontend
python -m http.server 3000
```

### 3. Flash the ESP32 Scanner
1. Open [`firmware/esp32_palm_scanner/esp32_palm_scanner.ino`](file:///d:/iot/firmware/esp32_palm_scanner/esp32_palm_scanner.ino) in Arduino IDE.
2. Set your WiFi credentials and PalmPay backend IP.
3. Select board `AI Thinker ESP32-CAM` with `PSRAM: Enabled` and flash over UART.
4. In the POS frontend, verify the ESP32 IP is entered in the status bar and click **Test Ping**.
