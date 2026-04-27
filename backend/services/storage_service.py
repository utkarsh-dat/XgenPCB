"""
Storage Service - High-performance local filesystem storage
"""
import uuid
import os
from pathlib import Path
from typing import Optional

from shared.config import get_settings


class StorageService:
    """Simplified storage: local filesystem only (MinIO removed for lean stack)"""

    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self.local_base = Path(settings.local_storage_path)
        self.local_base.mkdir(parents=True, exist_ok=True)

    def save_local(self, design_id: uuid.UUID, filename: str, content: bytes) -> Path:
        """Save file to local filesystem."""
        design_dir = self.local_base / str(design_id)
        design_dir.mkdir(parents=True, exist_ok=True)
        file_path = design_dir / filename
        file_path.write_bytes(content)
        return file_path

    def get_local_path(self, design_id: uuid.UUID, filename: str) -> Path:
        """Get local file path."""
        return self.local_base / str(design_id) / filename

    def local_exists(self, design_id: uuid.UUID, filename: str) -> bool:
        """Check if file exists locally."""
        return self.get_local_path(design_id, filename).exists()

    async def upload_dual(
        self, design_id: uuid.UUID, filename: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> dict:
        """Save to local filesystem (Dual-compat API but local-only)."""
        local_path = self.save_local(design_id, filename, content)
        # Return same schema for compatibility
        return {
            "local_path": str(local_path), 
            "minio_key": None, 
            "minio_url": None
        }


storage_service = StorageService()