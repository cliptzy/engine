import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.job_manager import job_manager

router = APIRouter()

class ClipRequest(BaseModel):
    url: str | None = None
    file_path: str | None = None
    # Add other parameters

@router.post("/clipper/analyze", status_code=202)
async def analyze_video(req: dict):
    # Dummy implementation for analyzing heatmap
    job = job_manager.create_job()
    return {"job_id": job.job_id, "status": job.status}

@router.post("/clipper/process", status_code=202)
async def process_clip(request: ClipRequest):
    job = job_manager.create_job()
    # async run
    return {"job_id": job.job_id, "status": job.status}

@router.post("/clipper/compile", status_code=202)
async def compile_clips(req: dict):
    job = job_manager.create_job()
    return {"job_id": job.job_id, "status": job.status}

@router.get("/clipper/progress/{job_id}")
async def get_progress(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "result": job.result,
        "error": job.error
    }

@router.post("/clipper/cancel/{job_id}")
async def cancel_job(job_id: str):
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job")
    return {"status": "cancelled"}
