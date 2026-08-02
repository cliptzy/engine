import os
import sys
import subprocess
from typing import Optional, Callable
from core.logger import log
from core.config import config

def get_video_codec_args() -> list:
    hw = getattr(config, "hw_accel", "cpu").lower()
    
    # Auto-redirect all hardware acceleration to VideoToolbox on macOS
    if sys.platform == "darwin" and hw in ["mac", "videotoolbox", "amd", "amf", "intel", "qsv", "nvidia", "nvenc"]:
        return ["-c:v", "h264_videotoolbox", "-b:v", "5M"]

    if hw in ["mac", "videotoolbox"]:
        return ["-c:v", "h264_videotoolbox", "-b:v", "5M"]
    elif hw in ["nvidia", "nvenc"]:
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "26"]
    elif hw in ["amd", "amf"]:
        return ["-c:v", "h264_amf", "-rc", "cqp", "-qp_p", "26", "-qp_i", "26"]
    elif hw in ["intel", "qsv"]:
        return ["-c:v", "h264_qsv", "-global_quality", "26"]
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26"]

def run_command_with_logging(cmd: list, event_hook: Optional[Callable], prefix: str = "") -> bool:
    """Helper to run a subprocess and stream its output line by line."""
    log.info(f"Running command: {' '.join(cmd)}")
    if callable(event_hook):
        event_hook("log", f"{prefix} Executing command: {' '.join(cmd)}\n")
        
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            if line:
                clean_line = line.strip()
                if clean_line:
                    log.info(f"{prefix} {clean_line}")
                    if callable(event_hook):
                        event_hook("log", f"{prefix} {clean_line}")
                    
        process.stdout.close()
    return_code = process.wait()
    
    if return_code != 0:
        msg = f"{prefix} Command failed with return code {return_code}"
        log.error(msg)
        if callable(event_hook):
            event_hook("log", msg)
        raise subprocess.CalledProcessError(return_code, cmd)
    return True

def cleanup_temp_files(files: list) -> None:
    """Safely removes temporary files."""
    for f in files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                log.debug(f"Failed to cleanup temp file {f}: {e}")
