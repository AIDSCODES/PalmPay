#!/usr/bin/env python
"""Palm vein dataset loader for PyTorch training"""
import os
import csv
import random
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass

import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms
from PIL import Image
import numpy as np


@dataclass
class PalmVeinSample:
    """Single palm vein sample"""
    image_path: str
    subject_id: str
    hand: str
    session: int
    wavelength: int
    dataset: str


class PalmVeinDataset(Dataset):
    """PyTorch Dataset for palm vein images"""

    def __init__(
        self,
        metadata_csv: str,
        transform: Optional[Callable] = None,
        target_size: Tuple[int, int] = (224, 224),
        augment: bool = False
    ):
        """
        Args:
            metadata_csv: Path to standardized metadata CSV
            transform: Custom transform (overrides default)
            target_size: Target image size (H, W)
            augment: Whether to apply training augmentations
        """
        self.metadata_csv = metadata_csv
        self.samples = self._load_metadata(metadata_csv)
        self.target_size = target_size
        self.augment = augment
        self.transform = transform or self._default_transform(augment)

    def _load_metadata(self, csv_path: str) -> List[PalmVeinSample]:
        """Load metadata from CSV"""
        samples = []
        csv_dir = Path(csv_path).parent
        # The image paths in CSV are relative to the dataset/ root
        dataset_root = csv_dir.parent if csv_dir.name in ['tongji', 'casia_ms', 'scut_pv', 'vera_palmvein', 'esp32_hardware', 'combined', 'synthetic_palmvein'] else csv_dir
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Resolve image path relative to dataset root
                image_path = dataset_root / row['image_path']
                samples.append(PalmVeinSample(
                    image_path=str(image_path),
                    subject_id=row['subject_id'],
                    hand=row['hand'],
                    session=int(row['session']),
                    wavelength=int(row['wavelength']),
                    dataset=row['dataset']
                ))
        return samples

    def _default_transform(self, augment: bool) -> Callable:
        """Create default transform pipeline"""
        transform_list = [
            transforms.Resize(self.target_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ]

        if augment:
            # Insert augmentations before resize
            aug_list = [
                transforms.RandomRotation(10),
                transforms.RandomAffine(degrees=0, translate=(0.05, 0.05), scale=(0.95, 1.05)),
                transforms.ColorJitter(brightness=0.15, contrast=0.15),
                transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.0)),
            ]
            transform_list = aug_list + transform_list

        return transforms.Compose(transform_list)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict:
        sample = self.samples[idx]

        # Load image
        try:
            image = Image.open(sample.image_path).convert('RGB')
        except Exception as e:
            raise RuntimeError(f"Failed to load {sample.image_path}: {e}")

        # Apply transforms
        image = self.transform(image)

        return {
            'image': image,
            'subject_id': sample.subject_id,
            'hand': sample.hand,
            'session': sample.session,
            'wavelength': sample.wavelength,
            'dataset': sample.dataset,
            'path': sample.image_path
        }


class TripletDataset(Dataset):
    """Dataset for triplet loss training (anchor, positive, negative)"""

    def __init__(
        self,
        metadata_csv: str,
        transform: Optional[Callable] = None,
        target_size: Tuple[int, int] = (224, 224),
        augment: bool = True
    ):
        self.metadata_csv = metadata_csv
        self.samples = self._load_metadata(metadata_csv)
        self.target_size = target_size
        self.transform = transform or self._default_transform(augment)

        # Group samples by subject_id for triplet mining
        self.subject_to_indices = {}
        for idx, sample in enumerate(self.samples):
            if sample.subject_id not in self.subject_to_indices:
                self.subject_to_indices[sample.subject_id] = []
            self.subject_to_indices[sample.subject_id].append(idx)

        self.subject_ids = list(self.subject_to_indices.keys())

    def _load_metadata(self, csv_path: str) -> List[PalmVeinSample]:
        samples = []
        csv_dir = Path(csv_path).parent
        dataset_root = csv_dir.parent if csv_dir.name in ['tongji', 'casia_ms', 'scut_pv', 'vera_palmvein', 'esp32_hardware', 'combined', 'synthetic_palmvein'] else csv_dir
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                image_path = dataset_root / row['image_path']
                samples.append(PalmVeinSample(
                    image_path=str(image_path),
                    subject_id=row['subject_id'],
                    hand=row['hand'],
                    session=int(row['session']),
                    wavelength=int(row['wavelength']),
                    dataset=row['dataset']
                ))
        return samples

    def _default_transform(self, augment: bool) -> Callable:
        transform_list = [
            transforms.Resize(self.target_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ]

        if augment:
            aug_list = [
                transforms.RandomRotation(10),
                transforms.RandomAffine(degrees=0, translate=(0.05, 0.05), scale=(0.95, 1.05)),
                transforms.ColorJitter(brightness=0.15, contrast=0.15),
                transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.0)),
            ]
            transform_list = aug_list + transform_list

        return transforms.Compose(transform_list)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict:
        anchor = self.samples[idx]

        # Select positive (same subject, different image)
        pos_indices = self.subject_to_indices[anchor.subject_id]
        if len(pos_indices) < 2:
            # Fallback: use same image with different augmentation
            pos_idx = idx
        else:
            pos_idx = random.choice([i for i in pos_indices if i != idx])

        # Select negative (different subject)
        neg_subject = random.choice([s for s in self.subject_ids if s != anchor.subject_id])
        neg_idx = random.choice(self.subject_to_indices[neg_subject])

        positive = self.samples[pos_idx]
        negative = self.samples[neg_idx]

        # Load and transform all three
        def load_and_transform(sample):
            img = Image.open(sample.image_path).convert('RGB')
            return self.transform(img)

        return {
            'anchor': load_and_transform(anchor),
            'positive': load_and_transform(positive),
            'negative': load_and_transform(negative),
            'anchor_subject': anchor.subject_id,
            'positive_subject': positive.subject_id,
            'negative_subject': negative.subject_id
        }


class CrossSessionDataset(Dataset):
    """Dataset for cross-session evaluation"""

    def __init__(
        self,
        metadata_csv: str,
        session: int,
        transform: Optional[Callable] = None,
        target_size: Tuple[int, int] = (224, 224)
    ):
        """Create dataset filtered by session"""
        self.metadata_csv = metadata_csv
        all_samples = self._load_metadata(metadata_csv)
        self.samples = [s for s in all_samples if s.session == session]
        self.transform = transform or self._default_transform()

    def _load_metadata(self, csv_path: str) -> List[PalmVeinSample]:
        samples = []
        csv_dir = Path(csv_path).parent
        dataset_root = csv_dir.parent if csv_dir.name in ['tongji', 'casia_ms', 'scut_pv', 'vera_palmvein', 'esp32_hardware', 'combined', 'synthetic_palmvein'] else csv_dir
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                image_path = dataset_root / row['image_path']
                samples.append(PalmVeinSample(
                    image_path=str(image_path),
                    subject_id=row['subject_id'],
                    hand=row['hand'],
                    session=int(row['session']),
                    wavelength=int(row['wavelength']),
                    dataset=row['dataset']
                ))
        return samples

    def _default_transform(self) -> Callable:
        return transforms.Compose([
            transforms.Resize(self.target_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict:
        sample = self.samples[idx]
        image = Image.open(sample.image_path).convert('RGB')
        image = self.transform(image)

        return {
            'image': image,
            'subject_id': sample.subject_id,
            'hand': sample.hand,
            'session': sample.session,
            'wavelength': sample.wavelength,
            'dataset': sample.dataset,
            'path': sample.image_path
        }


def create_dataloaders(
    metadata_csv: str,
    batch_size: int = 32,
    num_workers: int = 4,
    augment_train: bool = True,
    train_split: str = "train",
    val_split: str = "validation",
    test_split: str = "test"
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """Create train/val/test dataloaders from split CSVs"""

    base_dir = Path(metadata_csv).parent

    train_ds = PalmVeinDataset(
        str(base_dir / f"{train_split}.csv"),
        augment=augment_train
    )
    val_ds = PalmVeinDataset(
        str(base_dir / f"{val_split}.csv"),
        augment=False
    )
    test_ds = PalmVeinDataset(
        str(base_dir / f"{test_split}.csv"),
        augment=False
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    return train_loader, val_loader, test_loader


def create_triplet_dataloader(
    metadata_csv: str,
    batch_size: int = 32,
    num_workers: int = 4
) -> DataLoader:
    """Create dataloader for triplet loss training"""
    dataset = TripletDataset(metadata_csv, augment=True)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )


def get_subject_distribution(metadata_csv: str) -> Dict[str, int]:
    """Get number of samples per subject"""
    dist = {}
    with open(metadata_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row['subject_id']
            dist[sid] = dist.get(sid, 0) + 1
    return dist


def create_balanced_sampler(metadata_csv: str) -> WeightedRandomSampler:
    """Create sampler for balanced subject sampling"""
    dist = get_subject_distribution(metadata_csv)
    weights = []

    with open(metadata_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            weights.append(1.0 / dist[row['subject_id']])

    return WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)