"""Image preprocessing utilities"""
import base64
import io
import logging
from typing import Tuple, Optional
from PIL import Image
import numpy as np
import cv2
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """Palm image preprocessing pipeline"""

    def __init__(self):
        self.target_size = settings.IMAGE_TARGET_SIZE
        self.allowed_formats = settings.IMAGE_ALLOWED_FORMATS

    def decode_base64_image(self, base64_str: str) -> np.ndarray:
        """Decode base64 string to OpenCV image"""
        try:
            # Remove data URL prefix if present
            if base64_str.startswith("data:image"):
                base64_str = base64_str.split(",")[1]

            image_data = base64.b64decode(base64_str)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                raise ValueError("Failed to decode image")

            return image
        except Exception as e:
            logger.error(f"Image decode error: {e}")
            raise ValueError(f"Invalid image data: {e}")

    def validate_image(self, image: np.ndarray) -> Tuple[bool, list]:
        """Validate image format and quality"""
        issues = []

        if image is None:
            issues.append("Image is None")
            return False, issues

        if len(image.shape) != 3:
            issues.append("Image must be 3-channel (color)")
            return False, issues

        height, width = image.shape[:2]
        if height < 100 or width < 100:
            issues.append(f"Image too small: {width}x{height} (minimum 100x100)")
            return False, issues

        if height > 4000 or width > 4000:
            issues.append(f"Image too large: {width}x{height} (maximum 4000x4000)")
            return False, issues

        # Check for blank/uniform images
        if np.std(image) < 5:
            issues.append("Image appears to be blank or uniform")
            return False, issues

        return len(issues) == 0, issues

    def resize_image(self, image: np.ndarray) -> np.ndarray:
        """Resize image to target size maintaining aspect ratio"""
        target_h, target_w = self.target_size
        h, w = image.shape[:2]

        # Calculate scaling factor
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Resize
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Pad to target size
        pad_h = target_h - new_h
        pad_w = target_w - new_w
        top = pad_h // 2
        bottom = pad_h - top
        left = pad_w // 2
        right = pad_w - left

        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right,
            cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )

        return padded

    def enhance_vein_pattern(self, image: np.ndarray) -> np.ndarray:
        """Enhance palm vein patterns using CLAHE and filtering"""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # Merge back
        lab = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Apply bilateral filter for noise reduction while preserving edges
        filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)

        return filtered

    def extract_roi(self, image: np.ndarray) -> np.ndarray:
        """Extract Region of Interest (palm area)"""
        # For prototype: use center crop as ROI
        # In production: implement palm detection/segmentation
        h, w = image.shape[:2]
        target_h, target_w = self.target_size

        # Use center region
        roi_h = min(h, target_h)
        roi_w = min(w, target_w)
        start_h = (h - roi_h) // 2
        start_w = (w - roi_w) // 2

        roi = image[start_h:start_h + roi_h, start_w:start_w + roi_w]

        # Resize to exact target size if needed
        if roi.shape[:2] != (target_h, target_w):
            roi = cv2.resize(roi, (target_w, target_h), interpolation=cv2.INTER_AREA)

        return roi

    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """Normalize image for model input"""
        # Convert to float32 and normalize to [0, 1]
        normalized = image.astype(np.float32) / 255.0

        # Normalize with ImageNet stats (common for pretrained models)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (normalized - mean) / std

        return normalized

    def preprocess(self, base64_str: str) -> np.ndarray:
        """Complete preprocessing pipeline"""
        # Decode
        image = self.decode_base64_image(base64_str)

        # Validate
        is_valid, issues = self.validate_image(image)
        if not is_valid:
            raise ValueError(f"Image validation failed: {issues}")

        # Enhance vein patterns
        image = self.enhance_vein_pattern(image)

        # Extract ROI
        image = self.extract_roi(image)

        # Resize to target
        image = self.resize_image(image)

        # Normalize
        image = self.normalize_image(image)

        # Convert to CHW format for PyTorch
        image = np.transpose(image, (2, 0, 1))

        # Add batch dimension
        image = np.expand_dims(image, axis=0)

        return image

    def assess_quality(self, image: np.ndarray) -> float:
        """Assess image quality (0.0 to 1.0)"""
        # Convert to grayscale for quality assessment
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Calculate various quality metrics
        # 1. Sharpness (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(laplacian_var / 500.0, 1.0)

        # 2. Contrast (standard deviation)
        contrast_score = min(np.std(gray) / 64.0, 1.0)

        # 3. Brightness (should be in good range)
        mean_brightness = np.mean(gray)
        brightness_score = 1.0 - abs(mean_brightness - 128) / 128.0

        # Combined quality score
        quality = (sharpness_score * 0.4 + contrast_score * 0.3 + brightness_score * 0.3)

        return float(np.clip(quality, 0.0, 1.0))


# Global instance
image_processor = ImageProcessor()