from fastapi import APIRouter

router = APIRouter()

@router.post("/subtitle/transcribe")
async def transcribe(req: dict):
    return {"status": "accepted"}

@router.get("/subtitle/models")
async def list_models():
    return {"models": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]}

@router.post("/subtitle/models/download")
async def download_model(req: dict):
    return {"status": "downloading"}
