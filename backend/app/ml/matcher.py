"""Vector similarity matching using pgvector (PostgreSQL) or Python fallback (SQLite)"""
import numpy as np
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.biometric import BiometricTemplate
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import BiometricError

logger = get_logger(__name__)


class BiometricMatcher:
    """Biometric template matching using pgvector (PostgreSQL) or Python fallback (SQLite)"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.threshold = settings.BIOMETRIC_MATCH_THRESHOLD
        self._is_postgresql = db.bind.dialect.name == "postgresql" if db.bind else False

    async def find_match(
        self,
        query_embedding: np.ndarray,
        model_version: str,
        limit: int = 5
    ) -> List[Tuple[BiometricTemplate, float]]:
        """
        Find matching biometric templates using cosine similarity.

        Returns:
            List of (template, similarity_score) tuples, sorted by similarity desc
        """
        if self._is_postgresql:
            return await self._find_match_pgvector(query_embedding, model_version, limit)
        else:
            return await self._find_match_python(query_embedding, model_version, limit)

    async def _find_match_pgvector(
        self,
        query_embedding: np.ndarray,
        model_version: str,
        limit: int = 5
    ) -> List[Tuple[BiometricTemplate, float]]:
        """Find matches using pgvector (PostgreSQL)"""
        embedding_list = query_embedding.tolist()
        embedding_str = "[" + ",".join(map(str, embedding_list)) + "]"

        query = text("""
            SELECT bt.*, (bt.embedding <=> :embedding) as distance
            FROM biometric_templates bt
            WHERE bt.model_version = :model_version
              AND bt.revoked_at IS NULL
            ORDER BY bt.embedding <=> :embedding
            LIMIT :limit
        """)

        result = await self.db.execute(query, {
            "embedding": embedding_str,
            "model_version": model_version,
            "limit": limit
        })

        matches = []
        for row in result:
            template = BiometricTemplate(
                id=row.id,
                user_id=row.user_id,
                embedding=row.embedding,
                model_version=row.model_version,
                quality_score=row.quality_score,
                created_at=row.created_at,
                revoked_at=row.revoked_at
            )
            similarity = 1.0 - row.distance
            matches.append((template, similarity))

        return matches

    async def _find_match_python(
        self,
        query_embedding: np.ndarray,
        model_version: str,
        limit: int = 5
    ) -> List[Tuple[BiometricTemplate, float]]:
        """Find matches using Python cosine similarity (SQLite fallback)"""
        # Fetch all templates for the model version
        stmt = select(BiometricTemplate).where(
            BiometricTemplate.model_version == model_version,
            BiometricTemplate.revoked_at.is_(None)
        )
        result = await self.db.execute(stmt)
        templates = list(result.scalars().all())

        # Compute cosine similarity in Python
        matches = []
        for template in templates:
            template_embedding = np.array(template.embedding, dtype=np.float32)
            similarity = self._cosine_similarity(query_embedding, template_embedding)
            matches.append((template, similarity))

        # Sort by similarity descending and limit
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    async def find_best_match(
        self,
        query_embedding: np.ndarray,
        model_version: str
    ) -> Optional[Tuple[BiometricTemplate, float]]:
        """Find the single best match above threshold"""
        matches = await self.find_match(query_embedding, model_version, limit=1)

        if not matches:
            return None

        template, similarity = matches[0]

        if similarity >= self.threshold:
            return template, similarity

        return None

    async def check_duplicate(
        self,
        query_embedding: np.ndarray,
        model_version: str,
        exclude_user_id: Optional[UUID] = None
    ) -> Optional[Tuple[BiometricTemplate, float]]:
        """
        Check if a biometric template already exists (duplicate detection).
        Uses a higher threshold for duplicate detection.
        """
        DUPLICATE_THRESHOLD = 0.95  # Higher threshold for duplicate detection

        matches = await self.find_match(query_embedding, model_version, limit=3)

        for template, similarity in matches:
            if similarity >= DUPLICATE_THRESHOLD:
                if exclude_user_id is None or template.user_id != exclude_user_id:
                    return template, similarity

        return None

    async def get_user_templates(
        self,
        user_id: UUID,
        model_version: Optional[str] = None
    ) -> List[BiometricTemplate]:
        """Get all active biometric templates for a user"""
        query = select(BiometricTemplate).where(
            BiometricTemplate.user_id == user_id,
            BiometricTemplate.revoked_at.is_(None)
        )

        if model_version:
            query = query.where(BiometricTemplate.model_version == model_version)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def set_threshold(self, threshold: float) -> None:
        """Update matching threshold"""
        if not 0.0 <= threshold <= 1.0:
            raise BiometricError("Threshold must be between 0.0 and 1.0")
        self.threshold = threshold
        logger.info(f"Biometric match threshold updated to {threshold}")