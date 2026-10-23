# PalmPay - Palm Vein Biometric Payment Backend

A contactless palm-vein biometric payment system backend built with FastAPI, PostgreSQL, and pgvector.

## Architecture

```
ESP32 + IR Camera
       ↓
   HTTPS
       ↓
FastAPI Backend
       ↓
Authentication / Device Verification
       ↓
Image Validation
       ↓
Palm Image Preprocessing
       ↓
Palm-Vein AI Model
       ↓
Biometric Embedding
       ↓
pgvector Similarity Search
       ↓
User Identification
       ↓
Authentication
       ↓
Wallet Service
       ↓
Payment Service
       ↓
Transaction Database
```

## Features

- **Biometric Authentication**: Palm vein recognition using embedding-based architecture
- **User Registration**: Multi-sample enrollment without model retraining
- **Payment Processing**: Simulated wallet with atomic transactions
- **Device Management**: Secure ESP32 device authentication
- **Audit Logging**: Comprehensive event tracking
- **Idempotency**: Duplicate payment protection
- **Docker Support**: Full containerized deployment

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Database**: PostgreSQL 16 with pgvector extension
- **ORM**: SQLAlchemy 2.x (async)
- **Migrations**: Alembic
- **AI/ML**: PyTorch, OpenCV, NumPy
- **Security**: JWT, Argon2, HMAC
- **Testing**: pytest, httpx

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)

### Using Docker Compose

```bash
# Clone and navigate to backend
cd backend

# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend python scripts/migrate.py

# Create admin user and device
docker-compose exec backend python scripts/create_admin.py
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start PostgreSQL with pgvector
docker run -d \
  --name palmpay-postgres \
  -e POSTGRES_USER=palmpay \
  -e POSTGRES_PASSWORD=palmpay \
  -e POSTGRES_DB=palmpay \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Run migrations
python scripts/migrate.py

# Start server
uvicorn app.main:app --reload
```

## API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health (admin)

### Users
- `POST /api/v1/users/register` - Register new user with palm samples
- `GET /api/v1/users/{user_id}` - Get user details
- `PATCH /api/v1/users/{user_id}` - Update user

### Biometric
- `POST /api/v1/biometric/identify` - Identify user from palm image
- `POST /api/v1/biometric/verify` - Verify specific user (1:1)
- `POST /api/v1/biometric/enroll` - Enroll additional samples
- `POST /api/v1/biometric/quality` - Check image quality

### Wallets
- `GET /api/v1/wallets/{user_id}` - Get wallet balance
- `POST /api/v1/wallets/{user_id}/topup` - Top up wallet (admin)

### Payments
- `POST /api/v1/payments` - Process payment (requires Idempotency-Key header)

### Transactions
- `GET /api/v1/transactions/{user_id}` - Get transaction history
- `GET /api/v1/transactions/detail/{transaction_id}` - Get transaction details

### Devices
- `POST /api/v1/devices/register` - Register ESP32 device (admin)
- `POST /api/v1/devices/authenticate` - Authenticate device

### Admin
- `GET /api/v1/admin/users` - List users
- `POST /api/v1/admin/users/{user_id}/suspend` - Suspend user
- `POST /api/v1/admin/users/{user_id}/reactivate` - Reactivate user
- `GET /api/v1/admin/devices` - List devices
- `POST /api/v1/admin/devices/{device_id}/revoke` - Revoke device
- `GET /api/v1/admin/model/status` - Model status

## ESP32 Integration

### Registration Flow
```
ESP32 captures 3-5 palm images
       ↓
POST /api/v1/users/register (multipart/form-data)
  - name: string
  - phone: string (optional)
  - samples[]: image files
       ↓
Response: { success: true, user_id: "uuid", message: "..." }
```

### Identification Flow
```
ESP32 captures palm image
       ↓
POST /api/v1/biometric/identify (multipart/form-data)
  - image: image file
       ↓
Response: { matched: true, user_id: "uuid", similarity: 0.94 }
```

### Payment Flow
```
User identified
       ↓
POST /api/v1/payments (JSON)
  - user_id: "uuid"
  - amount: 500
  - currency: "INR"
  - merchant_id: "uuid" (optional)
Headers:
  - X-Device-ID: "uuid"
  - X-Device-Key: "secret"
  - Idempotency-Key: "uuid"
       ↓
Response: { success: true, transaction_id: "uuid", remaining_balance: 1500 }
```

## Configuration

Key environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://palmpay:palmpay@localhost:5432/palmpay` |
| `BIOMETRIC_MATCH_THRESHOLD` | Cosine similarity threshold | `0.85` |
| `BIOMETRIC_MODEL_PATH` | Path to trained model | `model/palm_vein_model.pt` |
| `USE_MOCK_MODEL` | Use development mock model | `true` |
| `DEVICE_AUTH_SECRET` | Device authentication secret | Required |
| `JWT_SECRET_KEY` | JWT signing secret | Required |
| `ADMIN_API_KEY` | Admin API key | Required |

## Database Schema

### Tables
- `users` - User accounts
- `biometric_templates` - Palm vein embeddings (pgvector)
- `wallets` - User wallets with Decimal balances
- `transactions` - Payment/Refund/Topup records
- `devices` - Registered ESP32 devices
- `audit_logs` - Security audit trail

### Vector Index
The `biometric_templates` table uses HNSW index for fast similarity search:
```sql
CREATE INDEX ix_biometric_templates_embedding_hnsw
ON biometric_templates USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## Biometric Model

The system uses an **embedding-based architecture**:

1. Palm image → CNN → 512-dim embedding vector
2. Embeddings stored in pgvector
3. Similarity search using cosine distance
4. New users register without model retraining

### Model Interface
```python
class PalmEmbeddingModel:
    def load() -> None
    def generate_embedding(image: np.ndarray) -> np.ndarray
    def validate_input(image: np.ndarray) -> bool
    def unload() -> None
```

### Development Mode
Set `USE_MOCK_MODEL=true` for development. The mock model generates deterministic embeddings based on image content.

### Production Model
Replace `MockPalmEmbeddingModel` with `PalmVeinModel` and provide trained weights.

## Model Training Pipeline

See **[DATASET.md](DATASET.md)** for complete dataset specifications and **[DATASET_LICENSES.md](DATASET_LICENSES.md)** for license tracking.

### Datasets
| Priority | Dataset | Purpose |
|----------|---------|---------|
| 1 | Tongji Contactless Palm Vein | Primary - NIR, contactless, multi-session |
| 2 | CASIA Multi-Spectral (850nm) | Secondary - NIR palm vein |
| 3 | SCUT_PV / VERA PalmVein | Additional NIR datasets |
| 4 | ESP32 Hardware Data | Real deployment validation |

### Training Pipeline
```bash
# 1. Standardize datasets to common format
python scripts/training/standardize_datasets.py

# 2. Train model (triplet loss / ArcFace / CosFace)
python scripts/training/train.py \
  --data dataset/combined/metadata.csv \
  --backbone resnet50 \
  --embedding-dim 512 \
  --loss triplet \
  --epochs 50 \
  --output model/palm_model_v1.pt

# 3. Evaluate on test set
python scripts/training/evaluate.py \
  --model model/palm_model_v1.pt \
  --test-data dataset/combined/test.csv

# 4. Cross-session evaluation (Tongji Session 1→2)
python scripts/training/evaluate.py \
  --model model/palm_model_v1.pt \
  --cross-session \
  --gallery-data dataset/tongji/train_session1.csv \
  --probe-data dataset/tongji/test_session2.csv

# 5. Cross-dataset generalization (Tongji → CASIA)
python scripts/training/evaluate.py \
  --model model/palm_model_v1.pt \
  --cross-dataset \
  --gallery-data dataset/tongji/metadata.csv \
  --test-data dataset/casia_ms/metadata.csv

# 6. ESP32 hardware validation (CRITICAL)
python scripts/training/evaluate.py \
  --model model/palm_model_v1.pt \
  --test-data dataset/esp32_hardware/metadata.csv

# 7. Convert for backend deployment
python scripts/training/convert_model.py \
  --checkpoint model/palm_model_v1.pt \
  --output model/palm_vein_model.pt \
  --format pytorch

# Or run complete pipeline
python scripts/training/pipeline.py
```

### ESP32 Data Collection
```bash
# Collect real hardware data
python scripts/training/collect_esp32_data.py \
  --subject esp32_001 \
  --session 1 \
  --hand left \
  --num-images 10
```

## Security

- **Device Authentication**: HMAC-based device key verification
- **Rate Limiting**: Configurable per-endpoint limits
- **Input Validation**: Strict Pydantic schemas
- **Audit Logging**: All sensitive operations logged
- **No Biometric Exposure**: Templates never returned in API responses
- **Idempotency**: Payment deduplication via Idempotency-Key header

## Anti-Spoofing

Liveness detection abstraction included:
```python
class LivenessDetector:
    def check(image: np.ndarray) -> Literal["live", "spoof", "unknown"]
```

Currently uses mock detector. Replace with production anti-spoofing model.

## Model Versioning

Each biometric template stores `model_version`. When model updates:
1. Register new model version
2. Re-enroll users or maintain backward compatibility
3. Similarity search only compares same-version embeddings

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_user_service.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Config, security, logging
│   ├── db/              # Database models & migrations
│   ├── ml/              # ML models & preprocessing
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── utils/           # Utilities
├── tests/               # Unit & integration tests
├── scripts/             # Utility scripts
│   └── training/        # ML training pipeline
├── dataset/             # Datasets (not in repo)
│   ├── tongji/
│   ├── casia_ms/
│   ├── scut_pv/
│   ├── vera_palmvein/
│   ├── esp32_hardware/
│   └── combined/
├── model/               # Model weights
├── alembic/             # Migrations
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── alembic.ini
├── DATASET.md           # Dataset documentation
└── DATASET_LICENSES.md  # Dataset license tracking
```

## ⚠️ Important Disclaimers

1. **Prototype Only**: This is a hackathon/prototype system, NOT suitable for real financial transactions
2. **Mock Model**: Default configuration uses a development mock model - NOT real biometric authentication
3. **No Real Payments**: Wallet and payment functionality is simulated
4. **Security**: Not production-hardened - requires security audit before deployment
5. **Privacy**: Biometric data handling must comply with local regulations (GDPR, BIPA, etc.)

## Production Considerations

Before production deployment:
- [ ] Replace mock model with trained palm vein model
- [ ] Implement real liveness detection
- [ ] Add HTTPS/TLS termination
- [ ] Configure proper secrets management
- [ ] Set up monitoring and alerting
- [ ] Conduct security audit
- [ ] Ensure regulatory compliance
- [ ] Implement backup and disaster recovery
- [ ] Add rate limiting with Redis
- [ ] Set up CI/CD pipeline

## License

MIT License - See LICENSE file for details.