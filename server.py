# server.py — Cliptzy AI Engine FastAPI Server
import os
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: preload heavy models
    from core.logger import log
    log.info("Cliptzy Engine starting up...")
    
    # Initialize Supabase from environment variables injected by Tauri
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY")
        
    if supabase_url and supabase_key:
        from core.supabase_sync import supabase_sync
        supabase_sync.initialize(supabase_url, supabase_key)
        log.info("Supabase sync initialized from Tauri injected env.")
    else:
        log.warning("SUPABASE_URL or SUPABASE_SECRET_KEY not found in env.")

    # Lazy-load models saat diperlukan, bukan di startup
    yield
    # Shutdown: cleanup
    log.info("Cliptzy Engine shutting down...")

app = FastAPI(
    title="Cliptzy AI Engine",
    version="4.0.0",
    lifespan=lifespan
)

# Register routers
from api.health import router as health_router
from api.clipper import router as clipper_router
from api.subtitle import router as subtitle_router
from api.upload import router as upload_router
from api.auth import router as auth_router

app.include_router(health_router)
app.include_router(clipper_router)
app.include_router(subtitle_router)
app.include_router(upload_router)
app.include_router(auth_router)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9721)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
