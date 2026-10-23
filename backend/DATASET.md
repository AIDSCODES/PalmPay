# PalmPay Dataset Documentation

This document describes the datasets used for training the palm-vein biometric embedding model.

## Dataset Priority

| Priority | Dataset | Description |
|----------|---------|-------------|
| 1 | **Tongji Contactless Palm Vein** | Primary dataset - contactless, NIR, multiple sessions |
| 2 | **CASIA Multi-Spectral (850 nm)** | Secondary - NIR subset for palm vein |
| 3 | **SCUT_PV / VERA PalmVein** | Optional additional NIR datasets |
| 4 | **ESP32 Hardware Data** | Real deployment domain validation |

---

## 1. Tongji Contactless Palm Vein Dataset

| Property | Value |
|----------|-------|
| **Name** | Tongji Contactless Palmprint and Palm Vein Dataset |
| **Subjects** | ~300 |
| **Images** | ~12,000 |
| **Wavelength** | 940 nm (IR) |
| **Modality** | Palm Vein (contactless) |
| **Sessions** | 2 |
| **Sensor** | Contactless NIR camera |
| **Resolution** | 640×480 (varies) |
| **Hand** | Left/Right |
| **License** | Research/Non-commercial (verify current terms) |
| **Source** | Tongji University |

### Directory Structure
```
dataset/tongji/
├── raw/                    # Original dataset files
├── processed/              # Preprocessed images
└── metadata.csv            # Standardized metadata
```

### Metadata Format
```csv
image_path,subject_id,hand,session,wavelength,modality,dataset
tongji/raw/001/image01.bmp,tongji_001,left,1,940,palm_vein,tongji
```

### Split Strategy
- **Subject-disjoint**: 80% train, 10% val, 10% test
- **Cross-session**: Session 1 → train, Session 2 → test

---

## 2. CASIA Multi-Spectral Palmprint Database V1.0

| Property | Value |
|----------|-------|
| **Name** | CASIA Multi-Spectral Palmprint Image Database V1.0 |
| **Subjects** | 100 |
| **Images** | 7,200 (total across wavelengths) |
| **Wavelengths** | 470, 525, 660, 850, 940 nm + White |
| **Relevant Wavelength** | 850 nm (palm vein) |
| **Modality** | Palm Vein (850 nm) / Palmprint (visible) |
| **Sessions** | 2 |
| **Resolution** | 640×480 |
| **License** | Research/Non-commercial (verify current terms) |
| **Source** | Chinese Academy of Sciences |

### Directory Structure
```
dataset/casia_ms/
├── raw/                    # Original dataset files
├── processed/              # Preprocessed 850 nm images
└── metadata.csv            # Standardized metadata (850 nm only)
```

### Metadata Format
```csv
image_path,subject_id,hand,session,wavelength,modality,dataset
casia_ms/raw/001/image01.bmp,casia_001,right,1,850,palm_vein,casia_ms
```

### Important: Wavelength Filtering
Only 850 nm images should be used for palm-vein training. Visible-light wavelengths (470, 525, 660 nm, white) are palmprint data and must be excluded from palm-vein experiments.

---

## 3. SCUT_PV (Optional)

| Property | Value |
|----------|-------|
| **Name** | SCUT Palm Vein Dataset |
| **Subjects** | 550 |
| **Images** | ~11,000 |
| **Wavelength** | NIR |
| **Modality** | Palm Vein |
| **Resolution** | Varies |
| **License** | Research (verify current terms) |
| **Source** | South China University of Technology |

---

## 4. VERA PalmVein (Optional)

| Property | Value |
|----------|-------|
| **Name** | VERA PalmVein Dataset |
| **Subjects** | 110 |
| **Images** | 2,200 |
| **Wavelength** | NIR |
| **Modality** | Palm Vein (contactless) |
| **License** | Research (verify current terms) |
| **Source** | VERA (Biometrics) |

---

## 5. ESP32 Hardware Dataset (Project-Specific)

| Property | Value |
|----------|-------|
| **Name** | PalmPay ESP32 Hardware Dataset |
| **Subjects** | Project-dependent |
| **Images** | Per participant: multiple captures |
| **Wavelength** | Matching ESP32 NIR camera |
| **Modality** | Palm Vein (contactless) |
| **Sessions** | Multiple per participant |
| **Sensor** | Actual ESP32 + NoIR camera + IR illumination |
| **License** | Project-owned (requires consent/ethics) |

### Capture Metadata
```csv
subject_id,capture_session,hand,image_path,capture_distance,lighting_condition,device_id
esp32_001,1,left,esp32/raw/001_1_left.jpg,15cm,indoor_ir,esp32_dev_01
```

---

## Standardized Metadata Format

All datasets are converted to a common format:

```csv
image_path,subject_id,hand,session,wavelength,modality,dataset
```

### Subject ID Namespacing
- `tongji_001`, `tongji_002`, ...
- `casia_001`, `casia_002`, ...
- `scut_001`, `scut_002`, ...
- `vera_001`, `vera_002`, ...
- `esp32_001`, `esp32_002`, ...

**NEVER** merge subject IDs across datasets without verified identity linkage.

---

## Dataset Split Strategy

### Primary Split (Subject-Disjoint)
```
Train:     80% of subjects
Validation: 10% of subjects
Test:      10% of subjects
```

### Cross-Session Evaluation (Tongji, CASIA)
```
Session 1 → Enrollment/Training
Session 2 → Testing
```

This represents the real application scenario where enrollment and authentication occur at different times.

---

## Experiments

### Experiment A: Tongji Only
- Train: Tongji (subject-disjoint split)
- Test: Tongji held-out subjects
- Cross-session: Session 1 train, Session 2 test

### Experiment B: CASIA 850nm Only
- Train: CASIA 850nm subset (subject-disjoint)
- Test: CASIA 850nm held-out subjects

### Experiment C: Combined NIR Training
- Train: Tongji + CASIA 850nm + other compatible NIR
- Test: Held-out subjects from all combined datasets

### Experiment D: Cross-Dataset Generalization
- Train: Tongji
- Test: CASIA 850nm (and vice versa)
- Measures domain generalization

### Experiment E: ESP32 Hardware Validation (CRITICAL)
- Train: Public datasets (A, B, or C)
- Test: ESP32 hardware dataset
- Measures real-world deployment performance

---

## Preprocessing Pipeline (Consistent Across All Stages)

```
Raw NIR Image
     |
     v
Image Quality Check
     |
     v
Palm Detection/ROI Extraction
     |
     v
Resize (224×224 or configurable)
     |
     v
Intensity Normalization
     |
     v
Optional Vein Enhancement (CLAHE, etc.)
     |
     v
AI Encoder
```

**Same pipeline must be used for:**
- Training
- Validation
- Testing
- Registration (enrollment)
- Authentication (inference)

---

## Data Augmentation (Training Only)

| Augmentation | Parameters |
|--------------|------------|
| Rotation | ±10° |
| Translation | ±5% |
| Scale | 0.95-1.05 |
| Brightness | ±15% |
| Contrast | ±15% |
| Blur | Mild (σ ≤ 1.0) |
| Sensor Noise | Mild Gaussian |

**Do NOT augment:**
- Test sets
- Validation sets (during evaluation)
- ESP32 hardware validation sets

---

## Model Architecture Target

```
Input: Preprocessed NIR Palm ROI (224×224×3)
     |
     v
CNN Backbone (ResNet/EfficientNet/MobileNet)
     |
     v
Embedding Layer (512-D or 256-D)
     |
     v
L2 Normalization
     |
     v
Output: Unit Embedding Vector
```

### Training Objective
**Metric Learning** (not classification):
- Triplet Loss / ArcFace / CosFace
- Learns: "What distinguishes one palm vein from another?"
- NOT: "Which of N training users is this?"

---

## Evaluation Metrics

| Metric | Purpose |
|--------|---------|
| **ROC / EER** | Verification performance |
| **Rank-1 / CMC** | Identification performance |
| **Cross-session EER** | Session generalization |
| **Cross-dataset EER** | Domain generalization |
| **ESP32 EER** | Real deployment performance |

---

## Threshold Calibration

After training, calibrate matching threshold using validation set:
- Target FAR (False Accept Rate): < 0.1%
- Target FRR (False Reject Rate): < 5%
- Operating point: Configurable via `BIOMETRIC_MATCH_THRESHOLD`

---

## Model Versioning

Each trained model gets a version:
```
palm_model_v1     # First production model
palm_model_v2     # Retrained with more data
palm_model_v3     # Architecture change
```

Stored in biometric templates:
```sql
model_version = 'palm_model_v1'
embedding_dim = 512
```

---

## License Compliance

See `DATASET_LICENSES.md` for detailed license information.

**Before using any dataset:**
1. Verify current license terms
2. Check commercial use restrictions
3. Confirm citation requirements
4. Document restrictions in `DATASET_LICENSES.md`

---

## Directory Structure Summary

```
dataset/
├── tongji/
│   ├── raw/
│   ├── processed/
│   └── metadata.csv
├── casia_ms/
│   ├── raw/
│   ├── processed/
│   └── metadata.csv
├── scut_pv/
│   ├── raw/
│   ├── processed/
│   └── metadata.csv
├── vera_palmvein/
│   ├── raw/
│   ├── processed/
│   └── metadata.csv
├── esp32_hardware/
│   ├── raw/
│   ├── processed/
│   └── metadata.csv
└── combined/
    ├── train/
    ├── validation/
    └── test/
```

---

## Citation Requirements

When using these datasets, cite the original publications:

```
# Tongji
@article{tongji_palmvein,
  title={Contactless Palm Vein Recognition...},
  author={...},
  journal={...},
  year={...}
}

# CASIA
@article{casia_multispectral,
  title={Multi-Spectral Palmprint Recognition...},
  author={...},
  journal={...},
  year={...}
}

# Add citations for other datasets used
```