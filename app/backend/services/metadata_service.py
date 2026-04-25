"""Metadata helpers shared by providers and API routes."""

from __future__ import annotations

from app.backend.models.download_result import MediaMetadata


class MetadataService:
    """Small seam for future metadata enrichment and library indexing."""

    def normalize(self, metadata: MediaMetadata) -> MediaMetadata:
        if metadata.title:
            metadata.title = metadata.title.strip()
        if metadata.artist:
            metadata.artist = metadata.artist.strip()
        return metadata

