from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "4.0.0"}

@router.get("/health/models")
async def model_status():
    # Cek apakah Whisper model sudah ter-cache, GPU tersedia, dll.
    return {"whisper_loaded": False, "gpu_available": False, "ffmpeg_available": True}
