#!/usr/bin/env python
"""
Synthetic Palm Vein Dataset Generator

Generates realistic-looking palm vein patterns for pipeline testing.
Uses procedural generation with Perlin noise, vascular tree structures,
and anatomical constraints to create plausible NIR palm vein images.

This allows immediate testing of the training pipeline while waiting
for real dataset access approvals.
"""
import os
import sys
import argparse
import logging
import csv
import random
import math
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass

import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageDraw

sys.path.append(str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SyntheticConfig:
    """Configuration for synthetic data generation"""
    num_subjects: int = 100
    images_per_subject: int = 20
    sessions: int = 2
    hands: List[str] = None
    wavelengths: List[int] = None
    image_size: Tuple[int, int] = (640, 480)
    output_format: str = 'bmp'
    seed: int = 42


class VascularTreeGenerator:
    """Generates realistic palm vein tree structures"""

    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        # Anatomical parameters
        self.palm_center = (320, 280)  # Approximate palm center in 640x480
        self.palm_radius = 140
        self.finger_bases = [
            (320, 100),   # Middle finger
            (260, 120),   # Index finger
            (380, 120),   # Ring finger
            (220, 160),   # Thumb
            (420, 160),   # Pinky
        ]

    def generate_vein_tree(self, subject_id: int, session: int, hand: str) -> np.ndarray:
        """Generate a unique vein pattern for a subject/session"""
        # Create deterministic but unique pattern per subject
        subject_seed = hash((subject_id, session, hand)) % (2**32)
        random.seed(subject_seed)
        np.random.seed(subject_seed)

        # Base canvas
        canvas = np.zeros((480, 640), dtype=np.float32)

        # Generate main venous trunks (3-5 major vessels)
        num_trunks = random.randint(3, 5)
        for _ in range(num_trunks):
            self._draw_venous_trunk(canvas)

        # Generate capillary network
        self._draw_capillary_network(canvas)

        # Add fingerprint-like ridge pattern (palmprint texture)
        self._add_palmprint_texture(canvas, subject_seed)

        # Add noise and variation
        canvas = self._add_imaging_artifacts(canvas, subject_seed)

        # Normalize to 0-255
        canvas = np.clip(canvas * 255, 0, 255).astype(np.uint8)

        return canvas

    def _draw_venous_trunk(self, canvas: np.ndarray):
        """Draw a main venous trunk with branches"""
        # Start from wrist area (bottom)
        start_x = random.randint(250, 390)
        start_y = random.randint(400, 460)

        # Main trunk direction (generally upward)
        angle = random.uniform(-math.pi/3, math.pi/3)  # ±60° from vertical
        length = random.randint(150, 250)

        # Trunk properties
        base_width = random.randint(4, 8)
        num_branches = random.randint(2, 5)

        self._draw_vessel_recursive(
            canvas, start_x, start_y, angle, length,
            base_width, num_branches, depth=0
        )

    def _draw_vessel_recursive(self, canvas: np.ndarray, x: float, y: float,
                                angle: float, length: int, width: int,
                                max_branches: int, depth: int):
        """Recursively draw vessel with branches"""
        if depth > 3 or length < 20 or width < 1:
            return

        # Calculate end point
        end_x = x + length * math.sin(angle)
        end_y = y - length * math.cos(angle)

        # Draw vessel segment with tapering
        num_points = max(10, length // 3)
        for i in range(num_points):
            t = i / num_points
            px = x + t * (end_x - x)
            py = y + t * (end_y - y)
            pw = int(width * (1 - t * 0.5))  # Taper

            if 0 <= px < 640 and 0 <= py < 480:
                cv2.circle(canvas, (int(px), int(py)), max(1, pw), 1.0, -1)

        # Branch
        if depth < 2 and max_branches > 0:
            num_branches = random.randint(1, max_branches)
            for _ in range(num_branches):
                branch_angle = angle + random.uniform(-math.pi/2, math.pi/2)
                branch_length = int(length * random.uniform(0.3, 0.7))
                branch_width = max(1, width - 1)
                self._draw_vessel_recursive(
                    canvas, end_x, end_y, branch_angle,
                    branch_length, branch_width,
                    max_branches - 1, depth + 1
                )

    def _draw_capillary_network(self, canvas: np.ndarray):
        """Draw fine capillary network using Perlin-like noise"""
        # Generate multiple layers of noise for capillary texture
        for scale in [8, 16, 32]:
            noise = self._generate_perlin_noise(480, 640, scale)
            # Only add in palm region
            mask = self._create_palm_mask()
            canvas += noise * mask * 0.15

    def _generate_perlin_noise(self, h: int, w: int, scale: int) -> np.ndarray:
        """Fast vectorized Perlin-like noise generation"""
        # Create grid of random gradients
        grid_h, grid_w = h // scale + 2, w // scale + 2
        gradients = np.random.randn(grid_h, grid_w, 2)
        gradients = gradients / np.linalg.norm(gradients, axis=2, keepdims=True)

        # Vectorized coordinates
        x_coords = np.arange(w) / scale
        y_coords = np.arange(h) / scale
        gx0 = np.floor(x_coords).astype(int)
        gy0 = np.floor(y_coords).astype(int)
        gx1 = gx0 + 1
        gy1 = gy0 + 1

        fx = x_coords - gx0
        fy = y_coords - gy0

        # Smooth interpolation
        u = fx * fx * (3 - 2 * fx)
        v = fy * fy * (3 - 2 * fy)

        # Vectorized dot products using broadcasting
        def dot_grid(gx, gy, dx, dy):
            gx = np.clip(gx, 0, grid_w - 1)
            gy = np.clip(gy, 0, grid_h - 1)
            return gradients[gy, gx, 0] * dx + gradients[gy, gx, 1] * dy

        # Compute all four corners
        n00 = dot_grid(gx0[:, None], gy0[None, :], fx[:, None], fy[None, :])
        n10 = dot_grid(gx1[:, None], gy0[None, :], fx[:, None] - 1, fy[None, :])
        n01 = dot_grid(gx0[:, None], gy1[None, :], fx[:, None], fy[None, :] - 1)
        n11 = dot_grid(gx1[:, None], gy1[None, :], fx[:, None] - 1, fy[None, :] - 1)

        # Bilinear interpolation
        nx0 = n00 * (1 - u[:, None]) + n10 * u[:, None]
        nx1 = n01 * (1 - u[:, None]) + n11 * u[:, None]
        noise = nx0 * (1 - v[None, :]) + nx1 * v[None, :]

        return noise.T  # Transpose to match (h, w)

    def _create_palm_mask(self) -> np.ndarray:
        """Create mask for palm region"""
        mask = np.zeros((480, 640), dtype=np.float32)
        cv2.circle(mask, self.palm_center, self.palm_radius, 1.0, -1)

        # Add finger regions
        for fx, fy in self.finger_bases:
            cv2.ellipse(mask, (fx, fy), (30, 60), 0, 0, 360, 1.0, -1)

        # Blur for smooth transition
        mask = cv2.GaussianBlur(mask, (31, 31), 10)
        return mask

    def _add_palmprint_texture(self, canvas: np.ndarray, seed: int):
        """Add palmprint ridge texture (visible in NIR too)"""
        random.seed(seed + 1000)
        np.random.seed(seed + 1000)

        # Generate parallel ridge pattern
        h, w = canvas.shape
        ridges = np.zeros((h, w), dtype=np.float32)

        # Primary ridge direction (slightly curved)
        for y in range(h):
            for x in range(w):
                # Distance from palm center
                dx = x - self.palm_center[0]
                dy = y - self.palm_center[1]
                dist = math.sqrt(dx*dx + dy*dy)

                if dist < self.palm_radius:
                    # Curved ridges
                    angle = math.atan2(dy, dx)
                    ridge_freq = 0.08
                    ridge_val = math.sin(dist * ridge_freq + angle * 3)
                    ridges[y, x] = max(0, ridge_val) * 0.1

        canvas += ridges

    def _add_imaging_artifacts(self, canvas: np.ndarray, seed: int) -> np.ndarray:
        """Add realistic imaging artifacts"""
        random.seed(seed + 2000)
        np.random.seed(seed + 2000)

        # Vignetting (darker edges)
        h, w = canvas.shape
        y_coords, x_coords = np.ogrid[:h, :w]
        center_y, center_x = h // 2, w // 2
        dist = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
        max_dist = math.sqrt(center_x**2 + center_y**2)
        vignette = 1 - 0.3 * (dist / max_dist)
        canvas = canvas * vignette

        # Sensor noise
        noise = np.random.normal(0, 0.02, canvas.shape).astype(np.float32)
        canvas = canvas + noise

        # Motion blur (slight)
        if random.random() < 0.3:
            kernel_size = random.randint(3, 5)
            kernel = np.zeros((kernel_size, kernel_size))
            kernel[kernel_size//2, :] = 1.0 / kernel_size
            canvas = cv2.filter2D(canvas, -1, kernel)

        # Non-uniform illumination
        illum = self._generate_perlin_noise(h, w, 64) * 0.2 + 0.9
        canvas = canvas * illum

        return np.clip(canvas, 0, 1)


class SyntheticDatasetGenerator:
    """Main dataset generator"""

    def __init__(self, config: SyntheticConfig):
        self.config = config
        if config.hands is None:
            config.hands = ['left', 'right']
        if config.wavelengths is None:
            config.wavelengths = [850, 940]

        self.vein_generator = VascularTreeGenerator(config.seed)
        self.records = []

    def generate(self, output_dir: str):
        """Generate complete synthetic dataset"""
        output_path = Path(output_dir)
        raw_dir = output_path / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating synthetic dataset:")
        logger.info(f"  Subjects: {self.config.num_subjects}")
        logger.info(f"  Images/subject: {self.config.images_per_subject}")
        logger.info(f"  Sessions: {self.config.sessions}")
        logger.info(f"  Hands: {self.config.hands}")
        logger.info(f"  Wavelengths: {self.config.wavelengths}")

        subject_count = 0
        for subject_idx in range(self.config.num_subjects):
            subject_id = f"syn_{subject_idx+1:04d}"
            subject_dir = raw_dir / subject_id
            subject_dir.mkdir(exist_ok=True)

            for session in range(1, self.config.sessions + 1):
                for hand in self.config.hands:
                    for wavelength in self.config.wavelengths:
                        # Distribute images across session/hand/wavelength
                        num_images = self.config.images_per_subject // (self.config.sessions * len(self.config.hands) * len(self.config.wavelengths))
                        if num_images == 0:
                            num_images = 1

                        for img_idx in range(num_images):
                            # Generate vein pattern
                            vein_image = self.vein_generator.generate_vein_tree(
                                subject_idx, session, hand
                            )

                            # Apply wavelength-specific characteristics
                            vein_image = self._apply_wavelength_effects(vein_image, wavelength)

                            # Save image
                            filename = f"{subject_id}_s{session}_{hand}_w{wavelength}_{img_idx+1:02d}.{self.config.output_format}"
                            filepath = subject_dir / filename

                            cv2.imwrite(str(filepath), vein_image)

                            # Record metadata
                            self.records.append({
                                'image_path': str(filepath.relative_to(output_path.parent)),
                                'subject_id': subject_id,
                                'hand': hand,
                                'session': session,
                                'wavelength': wavelength,
                                'modality': 'palm_vein',
                                'dataset': 'synthetic_palmvein'
                            })

            subject_count += 1
            if subject_count % 10 == 0:
                logger.info(f"  Generated {subject_count}/{self.config.num_subjects} subjects")

        # Write metadata CSV
        metadata_file = output_path / "metadata.csv"
        self._write_metadata(metadata_file)

        # Create standard splits
        self._create_splits(output_path)

        logger.info(f"Dataset generated at {output_path}")
        logger.info(f"Total images: {len(self.records)}")
        logger.info(f"Metadata: {metadata_file}")

    def _apply_wavelength_effects(self, image: np.ndarray, wavelength: int) -> np.ndarray:
        """Apply wavelength-specific imaging characteristics"""
        # 850nm: Stronger vein contrast, less surface detail
        # 940nm: Deeper penetration, different contrast
        if wavelength == 850:
            # Enhance contrast slightly
            image = cv2.convertScaleAbs(image, alpha=1.1, beta=0)
        elif wavelength == 940:
            # Slightly different texture
            image = cv2.convertScaleAbs(image, alpha=0.95, beta=5)
        return image

    def _write_metadata(self, metadata_file: Path):
        """Write metadata CSV"""
        with open(metadata_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'image_path', 'subject_id', 'hand', 'session',
                'wavelength', 'modality', 'dataset'
            ])
            writer.writeheader()
            writer.writerows(self.records)

    def _create_splits(self, output_path: Path):
        """Create train/val/test splits (subject-disjoint)"""
        import random
        random.seed(self.config.seed)

        # Group by subject
        subjects = {}
        for record in self.records:
            sid = record['subject_id']
            if sid not in subjects:
                subjects[sid] = []
            subjects[sid].append(record)

        subject_ids = list(subjects.keys())
        random.shuffle(subject_ids)

        n_total = len(subject_ids)
        n_train = int(n_total * 0.8)
        n_val = int(n_total * 0.1)

        train_subjects = set(subject_ids[:n_train])
        val_subjects = set(subject_ids[n_train:n_train + n_val])
        test_subjects = set(subject_ids[n_train + n_val:])

        for split_name, split_subjects in [
            ('train', train_subjects),
            ('validation', val_subjects),
            ('test', test_subjects)
        ]:
            split_records = [r for r in self.records if r['subject_id'] in split_subjects]
            split_file = output_path / f"{split_name}.csv"
            with open(split_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.records[0].keys())
                writer.writeheader()
                writer.writerows(split_records)
            logger.info(f"  {split_name}: {len(split_records)} images from {len(split_subjects)} subjects")

        # Cross-session splits (for Tongji-style evaluation)
        session1_records = [r for r in self.records if r['session'] == 1]
        session2_records = [r for r in self.records if r['session'] == 2]

        for split_name, split_records in [
            ('train_session1', session1_records),
            ('test_session2', session2_records)
        ]:
            split_file = output_path / f"{split_name}.csv"
            with open(split_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.records[0].keys())
                writer.writeheader()
                writer.writerows(split_records)
            logger.info(f"  {split_name}: {len(split_records)} images")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic palm vein dataset")
    parser.add_argument('--num-subjects', type=int, default=100)
    parser.add_argument('--images-per-subject', type=int, default=20)
    parser.add_argument('--sessions', type=int, default=2)
    parser.add_argument('--hands', nargs='+', default=['left', 'right'])
    parser.add_argument('--wavelengths', nargs='+', type=int, default=[850, 940])
    parser.add_argument('--image-size', nargs=2, type=int, default=[640, 480])
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    config = SyntheticConfig(
        num_subjects=args.num_subjects,
        images_per_subject=args.images_per_subject,
        sessions=args.sessions,
        hands=args.hands,
        wavelengths=args.wavelengths,
        image_size=tuple(args.image_size),
        seed=args.seed
    )

    generator = SyntheticDatasetGenerator(config)
    generator.generate(args.output)


if __name__ == "__main__":
    main()