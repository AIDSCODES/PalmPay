#!/usr/bin/env python
"""Collect ESP32 hardware dataset"""
import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import json
import csv
import base64

import cv2
import numpy as np

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.utils.image import image_processor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


class ESP32DataCollector:
    """Collect palm vein images from ESP32 hardware"""

    def __init__(self, output_dir: str = "dataset/esp32_hardware"):
        self.output_dir = Path(output_dir)
        self.raw_dir = self.output_dir / "raw"
        self.processed_dir = self.output_dir / "processed"
        self.metadata_file = self.output_dir / "metadata.csv"

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metadata file if not exists
        if not self.metadata_file.exists():
            with open(self.metadata_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'subject_id', 'capture_session', 'hand',
                    'image_path', 'capture_distance', 'lighting_condition',
                    'device_id', 'timestamp', 'quality_score'
                ])

    def capture_from_esp32(self, device_url: str, subject_id: str, session: int, hand: str,
                           capture_distance: str, lighting_condition: str, device_id: str) -> List[str]:
        """
        Capture images from ESP32 device.

        Args:
            device_url: ESP32 HTTP endpoint (e.g., http://192.168.1.100/capture)
            subject_id: Subject identifier
            session: Capture session number
            hand: 'left' or 'right'
            capture_distance: Distance from camera (e.g., '15cm')
            lighting_condition: Lighting description (e.g., 'indoor_ir')
            device_id: ESP32 device identifier

        Returns:
            List of saved image paths
        """
        import requests

        logger.info(f"Capturing from ESP32 {device_url} for {subject_id} session {session}")

        try:
            response = requests.post(
                f"{device_url}/capture",
                json={
                    "subject_id": subject_id,
                    "session": session,
                    "hand": hand
                },
                timeout=30
            )
            response.raise_for_status()

            # Assuming ESP32 returns base64 encoded image
            data = response.json()
            image_b64 = data.get('image')

            if not image_b64:
                logger.error("No image in response")
                return []

            # Save raw image
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{subject_id}_{session}_{hand}_{timestamp}.jpg"
            raw_path = self.raw_dir / filename

            image_data = base64.b64decode(image_b64)
            with open(raw_path, 'wb') as f:
                f.write(image_data)

            # Process and save processed version
            processed = image_processor.preprocess(image_b64)
            # Convert back to image for saving
            processed_img = (processed[0].transpose(1, 2, 0) * 255).astype(np.uint8)
            processed_path = self.processed_dir / filename
            cv2.imwrite(str(processed_path), cv2.cvtColor(processed_img, cv2.COLOR_RGB2BGR))

            # Quality assessment
            decoded = image_processor.decode_base64_image(image_b64)
            quality = image_processor.assess_quality(decoded)

            # Log metadata
            with open(self.metadata_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    subject_id, session, hand,
                    str(raw_path.relative_to(self.output_dir.parent)),
                    capture_distance, lighting_condition,
                    device_id, timestamp, quality
                ])

            logger.info(f"Captured {filename} (quality: {quality:.3f})")
            return [str(raw_path)]

        except Exception as e:
            logger.error(f"Capture failed: {e}")
            return []

    def capture_local_camera(self, camera_index: int, subject_id: str, session: int, hand: str,
                             capture_distance: str, lighting_condition: str, device_id: str,
                             num_images: int = 5) -> List[str]:
        """
        Capture images from local camera (for development/testing).

        Args:
            camera_index: OpenCV camera index
            subject_id: Subject identifier
            session: Capture session number
            hand: 'left' or 'right'
            capture_distance: Distance from camera
            lighting_condition: Lighting description
            device_id: Device identifier
            num_images: Number of images to capture

        Returns:
            List of saved image paths
        """
        cap = cv2.VideoCapture(camera_index)

        if not cap.isOpened():
            logger.error(f"Cannot open camera {camera_index}")
            return []

        # Set resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        saved_paths = []

        logger.info(f"Capturing {num_images} images for {subject_id} session {session}")
        logger.info("Press SPACE to capture, ESC to quit")

        count = 0
        while count < num_images:
            ret, frame = cap.read()
            if not ret:
                continue

            # Display preview
            preview = frame.copy()
            cv2.putText(preview, f"Subject: {subject_id} Session: {session} Hand: {hand}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(preview, f"Captured: {count}/{num_images} - SPACE to capture, ESC to quit",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Palm Vein Capture', preview)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            elif key == 32:  # SPACE
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"{subject_id}_{session}_{hand}_{timestamp}_{count}.jpg"
                raw_path = self.raw_dir / filename

                cv2.imwrite(str(raw_path), frame)

                # Process
                _, buffer = cv2.imencode('.jpg', frame)
                image_b64 = base64.b64encode(buffer).decode()

                processed = image_processor.preprocess(image_b64)
                processed_img = (processed[0].transpose(1, 2, 0) * 255).astype(np.uint8)
                processed_path = self.processed_dir / filename
                cv2.imwrite(str(processed_path), cv2.cvtColor(processed_img, cv2.COLOR_RGB2BGR))

                # Quality
                quality = image_processor.assess_quality(frame)

                # Log metadata
                with open(self.metadata_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        subject_id, session, hand,
                        str(raw_path.relative_to(self.output_dir.parent)),
                        capture_distance, lighting_condition,
                        device_id, timestamp, quality
                    ])

                saved_paths.append(str(raw_path))
                count += 1
                logger.info(f"Captured {filename} (quality: {quality:.3f})")

        cap.release()
        cv2.destroyAllWindows()

        return saved_paths


def main():
    parser = argparse.ArgumentParser(description="Collect ESP32 hardware dataset")
    parser.add_argument('--output', type=str, default='dataset/esp32_hardware', help='Output directory')
    parser.add_argument('--device-url', type=str, help='ESP32 HTTP endpoint')
    parser.add_argument('--camera', type=int, default=0, help='Local camera index')
    parser.add_argument('--subject', type=str, required=True, help='Subject ID')
    parser.add_argument('--session', type=int, default=1, help='Session number')
    parser.add_argument('--hand', type=str, choices=['left', 'right'], default='left', help='Hand')
    parser.add_argument('--distance', type=str, default='15cm', help='Capture distance')
    parser.add_argument('--lighting', type=str, default='indoor_ir', help='Lighting condition')
    parser.add_argument('--device-id', type=str, default='esp32_dev_01', help='Device ID')
    parser.add_argument('--num-images', type=int, default=5, help='Number of images to capture')
    args = parser.parse_args()

    collector = ESP32DataCollector(args.output)

    if args.device_url:
        collector.capture_from_esp32(
            args.device_url, args.subject, args.session, args.hand,
            args.distance, args.lighting, args.device_id
        )
    else:
        collector.capture_local_camera(
            args.camera, args.subject, args.session, args.hand,
            args.distance, args.lighting, args.device_id, args.num_images
        )

    logger.info("Data collection complete")


if __name__ == "__main__":
    main()