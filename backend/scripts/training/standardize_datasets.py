#!/usr/bin/env python
"""Dataset standardization and metadata generation"""
import os
import csv
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DatasetRecord:
    """Standardized dataset record"""
    image_path: str
    subject_id: str
    hand: str
    session: int
    wavelength: int
    modality: str
    dataset: str


class DatasetStandardizer:
    """Standardize different datasets to common format"""

    def __init__(self, base_path: str = "dataset"):
        self.base_path = Path(base_path)

    def standardize_tongji(self, raw_path: str, output_csv: str) -> List[DatasetRecord]:
        """
        Standardize Tongji dataset metadata.

        Expected raw structure:
        tongji/raw/
            001/
                001_01.tiff (session 1)
                001_02.tiff (session 1)
                ...
            002/
                ...

        Assumes:
        - Subject folders named 001, 002, etc.
        - Files named: {subject}_{index}.tiff where index 1-20
        - First 10 images = session 1, next 10 = session 2 (or similar split)
        - 940 nm wavelength
        """
        records = []
        raw_dir = Path(raw_path)

        for subject_dir in sorted(raw_dir.iterdir()):
            if not subject_dir.is_dir():
                continue

            subject_num = subject_dir.name
            subject_id = f"tongji_{subject_num}"

            # Support both .tiff and .bmp
            img_files = sorted(list(subject_dir.glob("*.tiff")) + list(subject_dir.glob("*.bmp")))

            for img_idx, img_file in enumerate(img_files):
                # Parse filename for session
                # Format: 001_01.tiff, 001_02.tiff, ..., 001_20.tiff
                # Assume first half = session 1, second half = session 2
                name = img_file.stem
                parts = name.split("_")

                if len(parts) >= 2:
                    img_num = int(parts[1]) if parts[1].isdigit() else (img_idx + 1)
                    # Split: first 10 = session 1, next 10 = session 2
                    session = 1 if img_num <= 10 else 2
                    hand = "left"  # Default
                else:
                    session = 1
                    hand = "left"

                record = DatasetRecord(
                    image_path=str(img_file.relative_to(self.base_path)),
                    subject_id=subject_id,
                    hand=hand,
                    session=session,
                    wavelength=940,
                    modality="palm_vein",
                    dataset="tongji"
                )
                records.append(record)

        self._write_csv(records, output_csv)
        logger.info(f"Tongji: {len(records)} records written to {output_csv}")
        return records

    def standardize_casia_ms(self, raw_path: str, output_csv: str, wavelength: int = 850) -> List[DatasetRecord]:
        """
        Standardize CASIA Multi-Spectral dataset metadata.

        Only processes images at the specified wavelength (default 850 nm for palm vein).

        Expected raw structure:
        casia_ms/raw/
            001/
                001_850_1.bmp
                001_850_2.bmp
                001_470_1.bmp  (ignored if wavelength=850)
            002/
                ...
        """
        records = []
        raw_dir = Path(raw_path)

        for subject_dir in sorted(raw_dir.iterdir()):
            if not subject_dir.is_dir():
                continue

            subject_num = subject_dir.name
            subject_id = f"casia_{subject_num}"

            for img_file in sorted(subject_dir.glob("*.bmp")):
                name = img_file.stem
                # Expected: subject_wavelength_session[_hand].bmp
                parts = name.split("_")

                if len(parts) >= 3:
                    try:
                        img_wavelength = int(parts[1])
                        if img_wavelength != wavelength:
                            continue  # Skip non-target wavelengths
                        session = int(parts[2]) if parts[2].isdigit() else 1
                        hand = parts[3] if len(parts) > 3 else "left"
                    except ValueError:
                        logger.warning(f"Could not parse: {name}")
                        continue
                else:
                    continue

                record = DatasetRecord(
                    image_path=str(img_file.relative_to(self.base_path)),
                    subject_id=subject_id,
                    hand=hand,
                    session=session,
                    wavelength=wavelength,
                    modality="palm_vein" if wavelength >= 800 else "palmprint",
                    dataset="casia_ms"
                )
                records.append(record)

        self._write_csv(records, output_csv)
        logger.info(f"CASIA-MS ({wavelength}nm): {len(records)} records written to {output_csv}")
        return records

    def standardize_scut_pv(self, raw_path: str, output_csv: str) -> List[DatasetRecord]:
        """Standardize SCUT_PV dataset metadata"""
        records = []
        raw_dir = Path(raw_path)

        for subject_dir in sorted(raw_dir.iterdir()):
            if not subject_dir.is_dir():
                continue

            subject_num = subject_dir.name
            subject_id = f"scut_{subject_num}"

            for img_file in sorted(subject_dir.glob("*.bmp")):
                name = img_file.stem
                parts = name.split("_")

                if len(parts) >= 2:
                    session = int(parts[1]) if parts[1].isdigit() else 1
                    hand = parts[2] if len(parts) > 2 else "left"
                else:
                    session = 1
                    hand = "left"

                record = DatasetRecord(
                    image_path=str(img_file.relative_to(self.base_path)),
                    subject_id=subject_id,
                    hand=hand,
                    session=session,
                    wavelength=850,  # Verify actual wavelength
                    modality="palm_vein",
                    dataset="scut_pv"
                )
                records.append(record)

        self._write_csv(records, output_csv)
        logger.info(f"SCUT_PV: {len(records)} records written to {output_csv}")
        return records

    def standardize_vera(self, raw_path: str, output_csv: str) -> List[DatasetRecord]:
        """Standardize VERA PalmVein dataset metadata"""
        records = []
        raw_dir = Path(raw_path)

        for subject_dir in sorted(raw_dir.iterdir()):
            if not subject_dir.is_dir():
                continue

            subject_num = subject_dir.name
            subject_id = f"vera_{subject_num}"

            for img_file in sorted(subject_dir.glob("*.bmp")):
                name = img_file.stem
                parts = name.split("_")

                if len(parts) >= 2:
                    session = int(parts[1]) if parts[1].isdigit() else 1
                    hand = parts[2] if len(parts) > 2 else "left"
                else:
                    session = 1
                    hand = "left"

                record = DatasetRecord(
                    image_path=str(img_file.relative_to(self.base_path)),
                    subject_id=subject_id,
                    hand=hand,
                    session=session,
                    wavelength=850,  # Verify actual wavelength
                    modality="palm_vein",
                    dataset="vera_palmvein"
                )
                records.append(record)

        self._write_csv(records, output_csv)
        logger.info(f"VERA: {len(records)} records written to {output_csv}")
        return records

    def standardize_esp32(self, raw_path: str, output_csv: str) -> List[DatasetRecord]:
        """Standardize ESP32 hardware dataset metadata"""
        records = []
        raw_dir = Path(raw_path)

        for img_file in sorted(raw_dir.glob("*.jpg")):
            name = img_file.stem
            # Expected: subject_session_hand.jpg
            parts = name.split("_")

            if len(parts) >= 3:
                subject_num = parts[0]
                subject_id = f"esp32_{subject_num}"
                session = int(parts[1]) if parts[1].isdigit() else 1
                hand = parts[2]
            else:
                subject_id = f"esp32_{name}"
                session = 1
                hand = "left"

            record = DatasetRecord(
                image_path=str(img_file.relative_to(self.base_path)),
                subject_id=subject_id,
                hand=hand,
                session=session,
                wavelength=940,  # Verify actual wavelength
                modality="palm_vein",
                dataset="esp32_hardware"
            )
            records.append(record)

        self._write_csv(records, output_csv)
        logger.info(f"ESP32 Hardware: {len(records)} records written to {output_csv}")
        return records

    def _write_csv(self, records: List[DatasetRecord], output_csv: str):
        """Write records to CSV"""
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['image_path', 'subject_id', 'hand', 'session', 'wavelength', 'modality', 'dataset'])
            for r in records:
                writer.writerow([r.image_path, r.subject_id, r.hand, r.session, r.wavelength, r.modality, r.dataset])

    def combine_metadata(self, csv_files: List[str], output_csv: str) -> List[DatasetRecord]:
        """Combine multiple metadata CSVs"""
        all_records = []
        for csv_file in csv_files:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    all_records.append(DatasetRecord(
                        image_path=row['image_path'],
                        subject_id=row['subject_id'],
                        hand=row['hand'],
                        session=int(row['session']),
                        wavelength=int(row['wavelength']),
                        modality=row['modality'],
                        dataset=row['dataset']
                    ))

        self._write_csv(all_records, output_csv)
        logger.info(f"Combined: {len(all_records)} records written to {output_csv}")
        return all_records

    def split_by_subject(self, csv_file: str, train_ratio: float = 0.8, val_ratio: float = 0.1, test_ratio: float = 0.1):
        """Create subject-disjoint train/val/test splits"""
        import random

        records = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)

        # Group by subject
        subjects = {}
        for r in records:
            sid = r['subject_id']
            if sid not in subjects:
                subjects[sid] = []
            subjects[sid].append(r)

        subject_ids = list(subjects.keys())
        random.shuffle(subject_ids)

        n_train = int(len(subject_ids) * train_ratio)
        n_val = int(len(subject_ids) * val_ratio)

        train_subjects = set(subject_ids[:n_train])
        val_subjects = set(subject_ids[n_train:n_train + n_val])
        test_subjects = set(subject_ids[n_train + n_val:])

        # Write splits
        for split_name, split_subjects in [('train', train_subjects), ('validation', val_subjects), ('test', test_subjects)]:
            split_records = [r for r in records if r['subject_id'] in split_subjects]
            output_file = Path(csv_file).parent / f"{split_name}.csv"
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(split_records)
            logger.info(f"{split_name}: {len(split_records)} images from {len(split_subjects)} subjects")

    def split_cross_session(self, csv_file: str, train_session: int = 1, test_session: int = 2):
        """Create cross-session splits (e.g., Session 1 train, Session 2 test)"""
        records = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)

        train_records = [r for r in records if int(r['session']) == train_session]
        test_records = [r for r in records if int(r['session']) == test_session]

        base_dir = Path(csv_file).parent
        for split_name, split_records in [('train_session1', train_records), ('test_session2', test_records)]:
            output_file = base_dir / f"{split_name}.csv"
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(split_records)
            logger.info(f"{split_name}: {len(split_records)} images")


def main():
    """Main standardization pipeline"""
    standardizer = DatasetStandardizer()

    # Standardize each dataset (uncomment when data is available)
    # standardizer.standardize_tongji("dataset/tongji/raw", "dataset/tongji/metadata.csv")
    # standardizer.standardize_casia_ms("dataset/casia_ms/raw", "dataset/casia_ms/metadata.csv", wavelength=850)
    # standardizer.standardize_scut_pv("dataset/scut_pv/raw", "dataset/scut_pv/metadata.csv")
    # standardizer.standardize_vera("dataset/vera_palmvein/raw", "dataset/vera_palmvein/metadata.csv")
    # standardizer.standardize_esp32("dataset/esp32_hardware/raw", "dataset/esp32_hardware/metadata.csv")

    # Combine all NIR datasets
    # csv_files = [
    #     "dataset/tongji/metadata.csv",
    #     "dataset/casia_ms/metadata.csv",
    #     "dataset/scut_pv/metadata.csv",
    #     "dataset/vera_palmvein/metadata.csv"
    # ]
    # standardizer.combine_metadata(csv_files, "dataset/combined/metadata.csv")

    # Create splits
    # standardizer.split_by_subject("dataset/combined/metadata.csv")
    # standardizer.split_cross_session("dataset/tongji/metadata.csv")

    logger.info("Standardization pipeline ready. Uncomment dataset calls when data is available.")


if __name__ == "__main__":
    main()