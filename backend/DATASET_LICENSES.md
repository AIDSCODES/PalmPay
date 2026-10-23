# PalmPay Dataset Licenses

This document tracks the licensing status of all datasets used in the project.

**⚠️ IMPORTANT**: License terms can change. Always verify current terms before downloading, processing, or using any dataset commercially.

---

## Tongji Contactless Palm Vein Dataset

| Field | Value |
|-------|-------|
| **Dataset** | Tongji Contactless Palmprint and Palm Vein Dataset |
| **Source** | Tongji University |
| **License** | Academic/Research use only (verify current terms) |
| **Commercial Use** | Typically restricted - verify |
| **Redistribution** | Typically not permitted - verify |
| **Publication of Images** | Typically restricted - verify |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

### Notes
- Contact Tongji University for latest license terms
- Many academic datasets restrict commercial use and redistribution
- If commercial use is needed, obtain explicit written permission

---

## CASIA Multi-Spectral Palmprint Database V1.0

| Field | Value |
|-------|-------|
| **Dataset** | CASIA Multi-Spectral Palmprint Image Database V1.0 |
| **Source** | Institute of Automation, Chinese Academy of Sciences (CASIA) |
| **License** | Research/Non-commercial (verify current terms) |
| **Commercial Use** | Restricted - verify with CASIA |
| **Redistribution** | Not permitted without permission |
| **Publication of Images** | Restricted |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

### Notes
- CASIA datasets typically require license agreement
- 850 nm subset may have different terms than full database
- Contact CASIA for commercial licensing

---

## SCUT_PV Dataset

| Field | Value |
|-------|-------|
| **Dataset** | SCUT Palm Vein Dataset (SCUT_PV) |
| **Source** | South China University of Technology |
| **License** | Research (verify current terms) |
| **Commercial Use** | Verify with SCUT |
| **Redistribution** | Verify |
| **Publication of Images** | Verify |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

---

## VERA PalmVein Dataset

| Field | Value |
|-------|-------|
| **Dataset** | VERA PalmVein |
| **Source** | VERA (Biometrics Evaluation) |
| **License** | Research (verify current terms) |
| **Commercial Use** | Verify with VERA organizers |
| **Redistribution** | Verify |
| **Publication of Images** | Verify |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

---

## PolyU Multi-Spectral Palmprint/Palm Vein

| Field | Value |
|-------|-------|
| **Dataset** | PolyU Multi-Spectral Palmprint/Palm Vein |
| **Source** | Hong Kong Polytechnic University |
| **License** | Research/Non-commercial (verify current terms) |
| **Commercial Use** | Restricted - verify with PolyU |
| **Redistribution** | Not permitted without permission |
| **Publication of Images** | Restricted |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

---

## IIT Delhi Touchless Palmprint Database

| Field | Value |
|-------|-------|
| **Dataset** | IIT Delhi Touchless Palmprint Database |
| **Source** | IIT Delhi |
| **License** | Academic use only |
| **Commercial Use** | Restricted |
| **Redistribution** | Not permitted |
| **Publication of Images** | Restricted |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

---

## PolyU-IITD Contactless Palmprint Database

| Field | Value |
|-------|-------|
| **Dataset** | PolyU-IITD Contactless Palmprint Database |
| **Source** | Hong Kong Polytechnic University + IIT Delhi |
| **License** | Research/Non-commercial |
| **Commercial Use** | Restricted |
| **Redistribution** | Not permitted |
| **Publication of Images** | Restricted |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

---

## PUT Vein Data

| Field | Value |
|-------|-------|
| **Dataset** | PUT Vein Database |
| **Source** | Poznan University of Technology |
| **License** | Research (verify current terms) |
| **Commercial Use** | Verify |
| **Redistribution** | Verify |
| **Publication of Images** | Verify |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

---

## PLUSVein-Contactless

| Field | Value |
|-------|-------|
| **Dataset** | PLUSVein-Contactless |
| **Source** | PLUSVein organizers |
| **License** | Research (verify current terms) |
| **Commercial Use** | Verify |
| **Redistribution** | Verify |
| **Publication of Images** | Verify |
| **Citation Required** | Yes |
| **Current Status** | **PENDING VERIFICATION** - Check latest terms before use |

---

## PalmPay ESP32 Hardware Dataset (Project-Owned)

| Field | Value |
|-------|-------|
| **Dataset** | PalmPay ESP32 Hardware Dataset |
| **Source** | Project data collection |
| **License** | Project-owned |
| **Commercial Use** | Permitted (with participant consent) |
| **Redistribution** | Project decision |
| **Publication of Images** | Requires explicit participant consent |
| **Ethics/IRB** | **REQUIRED** - Obtain ethics approval before collection |
| **Consent** | **REQUIRED** - Written informed consent from all participants |
| **Data Protection** | GDPR/PDPA/Applicable law compliance required |
| **Current Status** | **PROJECT-OWNED** - Full control with ethical obligations |

### Participant Consent Requirements
- Written informed consent
- Clear explanation of biometric data use
- Right to withdraw
- Data retention/deletion policy
- Anonymization requirements

---

## Summary: Commercial Use Assessment

| Dataset | Commercial Use Allowed? | Action Required |
|---------|------------------------|-----------------|
| Tongji | ❌ Likely No | Verify + Request permission |
| CASIA-MS | ❌ Likely No | Verify + Request permission |
| SCUT_PV | ❓ Unknown | Verify |
| VERA PalmVein | ❓ Unknown | Verify |
| PolyU Multi-Spectral | ❌ Likely No | Verify + Request permission |
| IIT Delhi Touchless | ❌ No | Academic only |
| PolyU-IITD Contactless | ❌ No | Academic only |
| PUT Vein | ❓ Unknown | Verify |
| PLUSVein | ❓ Unknown | Verify |
| ESP32 Hardware | ✅ Yes (with consent) | Ethics approval + Consent |

---

## Recommendation for Production

If the PalmPay system is intended for **commercial deployment**:

1. **Do not use** datasets with non-commercial licenses for training the production model
2. **Options:**
   - Obtain commercial licenses from dataset owners
   - Collect and use only project-owned ESP32 hardware data
   - Use datasets with explicit commercial-friendly licenses
   - Train on public datasets, validate on ESP32 data, but document license limitations

3. **Document everything** in this file and keep records of:
   - License agreements
   - Correspondence with dataset providers
   - Ethics approvals
   - Participant consent forms

---

## Verification Checklist

Before using any dataset, complete:

- [ ] Current license terms obtained and reviewed
- [ ] Commercial use permission confirmed (if needed)
- [ ] Redistribution rights confirmed (if needed)
- [ ] Image publication rights confirmed (if needed)
- [ ] Citation requirements documented
- [ ] Entry added to this file with date
- [ ] Legal review completed (for production)

---

*Last Updated: 2026*
*Next Review: Before any production deployment*