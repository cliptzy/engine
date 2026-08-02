from pathlib import Path
from typing import List, Optional
from core.interfaces import BaseUploader, ProgressReporter

class UploadClipUseCase:
    def __init__(self, uploader: BaseUploader, reporter: Optional[ProgressReporter] = None):
        self.uploader = uploader
        self.reporter = reporter

    def execute(self, video_path: Path, title: str, description: str, tags: List[str]) -> bool:
        """
        Uploads a video to the target platform using the injected uploader.
        """
        if self.reporter:
            self.reporter.on_log(f"Starting upload for {video_path.name}")
        
        success = self.uploader.upload(video_path, title, description, tags)
        
        if self.reporter:
            if success:
                self.reporter.on_log(f"Upload successful for {video_path.name}")
                self.reporter.on_finished(video_path)
            else:
                self.reporter.on_error(f"Upload failed for {video_path.name}")
                
        return success
