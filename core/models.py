import sys
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    TypeAlias = str


@dataclass
class VideoInfo:
    """Represents metadata of a fetched video."""
    video_id: str
    title: str
    duration: float
    url: str
    thumbnail_url: Optional[str] = None


@dataclass
class ClipSegment:
    """Represents a highlight or segment of a video to be clipped."""
    start_time: float
    end_time: float
    label: str
    score: float = 0.0


@dataclass
class ClipResult:
    """Result of a video clipping process."""
    output_path: Path
    duration: float
    success: bool
    error: Optional[str] = None
