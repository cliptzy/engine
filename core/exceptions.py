"""Custom exception hierarchy for Cliptzy."""

class CliptzyError(Exception):
    """Base exception for all Cliptzy errors."""
    pass

class VideoDownloadError(CliptzyError):
    """Raised when downloading a video fails."""
    pass

class ProcessingError(CliptzyError):
    """Raised when video processing fails."""
    pass

class TranscriptionError(CliptzyError):
    """Raised when audio transcription (Whisper) fails."""
    pass

class UploadError(CliptzyError):
    """Raised when video upload fails."""
    pass

class ConfigError(CliptzyError):
    """Raised when there is a configuration error."""
    pass

class FFmpegError(ProcessingError):
    """Raised when an FFmpeg subprocess fails."""
    pass

class CancellationError(CliptzyError):
    """Raised when a task is cancelled by the user."""
    pass
