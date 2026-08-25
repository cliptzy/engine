from fastapi import APIRouter

router = APIRouter()

@router.post("/upload/youtube")
async def upload_youtube(req: dict):
    return {"status": "queued"}

@router.post("/upload/tiktok")
async def upload_tiktok(req: dict):
    return {"status": "queued"}

@router.post("/upload/instagram")
async def upload_instagram(req: dict):
    return {"status": "queued"}

@router.get("/upload/status/{job_id}")
async def upload_status(job_id: str):
    return {"status": "pending"}
