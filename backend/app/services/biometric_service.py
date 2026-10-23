"""Biometric service"""
from typing import List, Optional, Tuple
from uuid import UUID
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User, UserStatus
from app.db.models.biometric import BiometricTemplate
from app.ml.embedding import embedding_service
from app.ml.matcher import BiometricMatcher
from app.ml.liveness import liveness_detector
from app.utils.image import image_processor
from app.core.logging import get_logger
from app.core.exceptions import (
    BiometricError,
    ValidationError,
    NotFoundError,
    ConflictError,
    ModelError
)

logger = get_logger(__name__)


class BiometricService:
    """Biometric enrollment and identification service"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.matcher = BiometricMatcher(db)

    async def enroll_user(
        self,
        user_id: UUID,
        images: List[str],  # base64 encoded images
        model_version: str = None
    ) -> Tuple[List[BiometricTemplate], List[float]]:
        """
        Enroll a user with multiple palm images.

        Returns:
            Tuple of (templates, quality_scores)
        """
        if model_version is None:
            model_version = embedding_service.model_version

        if len(images) < 3:
            raise ValidationError("At least 3 images required for enrollment")
        if len(images) > 5:
            raise ValidationError("Maximum 5 images allowed for enrollment")

        # Process each image
        embeddings = []
        quality_scores = []
        templates = []

        for i, base64_image in enumerate(images):
            # Preprocess
            try:
                preprocessed = image_processor.preprocess(base64_image)
            except ValueError as e:
                raise ValidationError(f"Image {i+1} preprocessing failed: {e}")

            # Quality check
            # Decode again for quality assessment
            decoded = image_processor.decode_base64_image(base64_image)
            quality = image_processor.assess_quality(decoded)

            if quality < 0.5:  # Minimum quality threshold
                raise ValidationError(f"Image {i+1} quality too low: {quality:.2f}")

            quality_scores.append(quality)

            # Generate embedding
            try:
                embedding = embedding_service.generate_embedding(preprocessed)
            except Exception as e:
                raise ModelError(f"Embedding generation failed for image {i+1}: {e}")

            embeddings.append(embedding)

        # Check consistency between samples
        is_consistent, avg_sim, min_sim = embedding_service.check_consistency(embeddings)
        if not is_consistent:
            raise BiometricError(
                f"Enrollment samples inconsistent (min similarity: {min_sim:.2f})",
                code="LOW_IMAGE_QUALITY"
            )

        # Check for duplicate (different user with same biometric)
        duplicate = await self.matcher.check_duplicate(embeddings[0], model_version)
        if duplicate:
            raise ConflictError("Biometric already registered to another user", code="BIOMETRIC_DUPLICATE")

        # Create templates
        for embedding, quality in zip(embeddings, quality_scores):
            template = BiometricTemplate(
                user_id=user_id,
                embedding=embedding.tolist(),
                model_version=model_version,
                quality_score=quality
            )
            self.db.add(template)
            templates.append(template)

        await self.db.flush()
        return templates, quality_scores

    async def identify(
        self,
        base64_image: str,
        model_version: str = None
    ) -> Tuple[bool, Optional[UUID], Optional[float], Optional[str]]:
        """
        Identify user from palm image.

        Returns:
            (matched, user_id, similarity, reason)
        """
        if model_version is None:
            model_version = embedding_service.model_version

        # Liveness check
        decoded = image_processor.decode_base64_image(base64_image)
        liveness_result = liveness_detector.check(decoded)
        if liveness_result == "spoof":
            return False, None, None, "SPOOF_DETECTED"

        # Preprocess
        try:
            preprocessed = image_processor.preprocess(base64_image)
        except ValueError as e:
            raise ValidationError(f"Image preprocessing failed: {e}")

        # Quality check
        quality = image_processor.assess_quality(decoded)
        if quality < 0.5:
            return False, None, None, "LOW_IMAGE_QUALITY"

        # Generate embedding
        try:
            embedding = embedding_service.generate_embedding(preprocessed)
        except Exception as e:
            raise ModelError(f"Embedding generation failed: {e}")

        # Find match
        match = await self.matcher.find_best_match(embedding, model_version)

        if match:
            template, similarity = match
            # Verify user is active
            stmt = select(User).where(User.id == template.user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if user and user.status == UserStatus.ACTIVE:
                return True, template.user_id, similarity, None
            else:
                return False, None, similarity, "USER_INACTIVE"

        return False, None, None, "NO_MATCH"

    async def verify_user(
        self,
        user_id: UUID,
        base64_image: str,
        model_version: str = None
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Verify a specific user (1:1 matching).

        Returns:
            (matched, similarity, reason)
        """
        if model_version is None:
            model_version = embedding_service.model_version

        # Get user's templates
        templates = await self.matcher.get_user_templates(user_id, model_version)
        if not templates:
            return False, None, "NO_TEMPLATE"

        # Preprocess and generate embedding
        try:
            preprocessed = image_processor.preprocess(base64_image)
            embedding = embedding_service.generate_embedding(preprocessed)
        except Exception as e:
            raise ModelError(f"Processing failed: {e}")

        # Compare against all user templates
        best_similarity = 0.0
        for template in templates:
            template_embedding = np.array(template.embedding)
            similarity = embedding_service.compute_similarity(embedding, template_embedding)
            best_similarity = max(best_similarity, similarity)

        if best_similarity >= self.matcher.threshold:
            return True, best_similarity, None

        return False, best_similarity, "NO_MATCH"

    async def revoke_template(self, template_id: UUID) -> BiometricTemplate:
        """Revoke a biometric template"""
        stmt = select(BiometricTemplate).where(BiometricTemplate.id == template_id)
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise NotFoundError("Biometric template not found")

        from datetime import datetime
        template.revoked_at = datetime.utcnow()
        await self.db.flush()
        return template

    async def get_user_templates(self, user_id: UUID) -> List[BiometricTemplate]:
        """Get all active templates for a user"""
        return await self.matcher.get_user_templates(user_id)