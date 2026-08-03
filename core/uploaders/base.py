from typing import Protocol, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class UploadResult:
    success: bool
    platform: str
    url: Optional[str] = None
    error_msg: Optional[str] = None

class BaseUploader(Protocol):
    platform_name: str
    
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        """
        Uploads the given file to the platform.
        metadata contains keys like: 'title', 'description', 'privacy', 'tags'.
        event_hook(kind: str, data: Any) is used to report progress or detailed logs.
        """
        ...

    def close(self) -> None:
        """Clean up resources (like browsers) if needed."""
        ...
