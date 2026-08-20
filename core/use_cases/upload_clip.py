from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.interfaces import ProgressReporter
from core.uploaders.base import BaseUploader


class UploadClipUseCase:
    def __init__(
        self, uploader: BaseUploader, reporter: Optional[ProgressReporter] = None
    ):
        self.uploader = uploader
        self.reporter = reporter

    def execute(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str],
        publish_at: Optional[datetime] = None,
    ) -> bool:
        """
        Uploads a video to the target platform using the injected uploader.
        """
        if self.reporter:
            self.reporter.on_log(f"Starting upload for {video_path.name}")

        metadata: Dict[str, Any] = {
            "title": title,
            "description": description,
            "tags": tags,
        }

        if publish_at:
            publish_time_utc = publish_at.astimezone(timezone.utc)
            metadata["publish_at"] = publish_time_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Generate thumbnail dynamically for all uploaded products
        from core.processing.thumbnail import generate_thumbnail
        import os
        
        thumbnail_path = os.path.splitext(str(video_path))[0] + "_thumbnail.jpg"
        if generate_thumbnail(str(video_path), thumbnail_path, metadata):
            metadata["thumbnail_path"] = thumbnail_path

        def hook(kind, data):
            if self.reporter and kind == "log":
                self.reporter.on_log(str(data))

        result = self.uploader.upload(str(video_path), metadata, event_hook=hook)

        if self.reporter:
            if result.success:
                self.reporter.on_log(f"Upload successful for {video_path.name}")
                self.reporter.on_finished(video_path)
            else:
                self.reporter.on_error(
                    f"Upload failed for {video_path.name}: {result.error_msg}"
                )

        return result.success
