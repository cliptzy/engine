import os
import json
import subprocess
import sys
import threading
import time
import uuid

from flask import Flask, jsonify, render_template, request, send_from_directory

from core import (
    config,
    log,
    check_dependencies,
    extract_video_id,
    fetch_most_replayed,
    get_video_duration,
    process_single_clip
)

app = Flask(__name__, static_folder="static", template_folder="templates")

jobs_lock = threading.Lock()
jobs = {}
preview_lock = threading.Lock()
preview_cache = {}

def now_ms() -> int:
    return int(time.time() * 1000)

def safe_int(value, default=None):
    try:
        return int(value)
    except Exception:
        return default

def parse_time_to_seconds(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    parts = s.split(":")
    if len(parts) == 2:
        m, sec = parts
        return int(m) * 60 + int(float(sec))
    if len(parts) == 3:
        h, m, sec = parts
        return int(h) * 3600 + int(m) * 60 + int(float(sec))
    return None

def set_job(job_id, **patch):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job.update(patch)

def add_log(job_id, line):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job["logs"].append(line)
        if len(job["logs"]) > 300:
            job["logs"] = job["logs"][-300:]
    log.info(f"[Job {job_id}] {line}")

def list_outputs(job_dir):
    if not os.path.isdir(job_dir):
        return []
    items = []
    for name in os.listdir(job_dir):
        path = os.path.join(job_dir, name)
        if os.path.isfile(path) and name.lower().endswith(".mp4"):
            items.append({"name": name, "size": os.path.getsize(path)})
    items.sort(key=lambda x: x["name"])
    return items

def run_job(job_id, payload):
    started = now_ms()
    try:
        set_job(job_id, status="running", started_at=started)

        url = (payload.get("url") or "").strip()
        if not url:
            raise ValueError("Empty URL")

        crop = payload.get("crop") or "default"
        ratio = payload.get("ratio") or "9:16"
        subtitle = bool(payload.get("subtitle"))
        whisper_model = payload.get("whisper_model") or "small"
        subtitle_font = payload.get("subtitle_font") or "Arial"
        subtitle_location = payload.get("subtitle_location") or "bottom"
        subtitle_fontsdir = payload.get("subtitle_fontsdir") or None
        
        try:
            subtitle_delay = float(payload.get("subtitle_delay") or 0.0)
        except ValueError:
            subtitle_delay = 0.0
            
        if not subtitle_fontsdir and os.path.isdir("fonts"):
            subtitle_fontsdir = "fonts"
            
        padding = safe_int(payload.get("padding"), 10)
        max_clips = safe_int(payload.get("max_clips"), 10)
        mode = payload.get("mode") or "heatmap"
        
        set_job(job_id, subtitle_enabled=subtitle)

        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")

        # Update application configuration
        config.whisper_model = whisper_model
        config.subtitle_font = subtitle_font
        config.subtitle_fonts_dir = subtitle_fontsdir
        config.subtitle_location = subtitle_location
        config.subtitle_delay = subtitle_delay / 1000.0  # Convert ms to seconds
        config.padding = max(0, padding if padding is not None else 10)
        config.set_ratio_preset(ratio)

        job_dir = os.path.join("clips", video_id)
        os.makedirs(job_dir, exist_ok=True)
        config.output_dir = job_dir

        ok = check_dependencies(install_whisper=subtitle, skip_update_ytdlp=True, fatal=False, whisper_model=whisper_model)
        if not ok:
            raise RuntimeError("FFmpeg not found")

        total_duration = get_video_duration(video_id)

        targets = []
        picked = payload.get("segments")
        if isinstance(picked, list) and len(picked) > 0:
            add_log(job_id, f"Using {len(picked)} selected segments...")
            for seg in picked:
                try:
                    start = float(seg.get("start"))
                    dur = float(seg.get("duration"))
                    score = float(seg.get("score", 1.0))
                except Exception:
                    continue
                if dur <= 0:
                    continue
                targets.append({"start": start, "duration": dur, "score": score})
            if not targets:
                raise ValueError("Selected segments are invalid")
        elif mode == "custom":
            start_s = parse_time_to_seconds(payload.get("start"))
            end_s = parse_time_to_seconds(payload.get("end"))
            if start_s is None or end_s is None:
                raise ValueError("Start/End times must be provided")
            if end_s <= start_s:
                raise ValueError("End time must be greater than Start time")
            targets = [{"start": float(start_s), "duration": float(end_s - start_s), "score": 1.0}]
        else:
            add_log(job_id, "Scanning heatmap...")
            segments = fetch_most_replayed(video_id, config.min_score, config.max_duration)
            if not segments:
                raise RuntimeError("No heatmap / Most Replayed data available for this video")
            targets = segments[: max(1, max_clips or 10)]

        set_job(job_id, total=len(targets), done=0, status_text="processing")

        def event_hook(kind, data):
            if kind == "log":
                add_log(job_id, str(data))
                return
            if kind != "stage" or not isinstance(data, dict):
                return
            stage = data.get("stage") or ""
            clip_index = safe_int(data.get("clip_index"), 0) or 0
            set_job(job_id, stage=stage, stage_at=now_ms(), stage_clip=clip_index)

        success = 0
        for idx, item in enumerate(targets, start=1):
            set_job(job_id, current=idx, status_text=f"clip {idx}/{len(targets)}")
            ok = process_single_clip(
                video_id=video_id,
                item=item,
                index=idx,
                total_duration=total_duration,
                crop_mode=crop,
                use_subtitle=subtitle,
                event_hook=event_hook
            )
            if ok:
                success += 1
            set_job(job_id, done=idx, success=success, outputs=list_outputs(job_dir))

        set_job(job_id, status="done", finished_at=now_ms(), outputs=list_outputs(job_dir))
    except Exception as e:
        log.exception(f"Job {job_id} failed: {e}")
        set_job(job_id, status="error", error=str(e), finished_at=now_ms())


@app.get("/")
def index():
    return render_template("index.html")

@app.get("/assets/fonts/<path:filename>")
def serve_font(filename):
    return send_from_directory("fonts", filename, as_attachment=False)

def get_preview(url):
    key = url.strip()
    if not key:
        raise ValueError("Empty URL")

    with preview_lock:
        cached = preview_cache.get(key)
        if cached:
            return cached

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--skip-download",
        "-J",
    ]
    
    if config.cookies_file and os.path.exists(config.cookies_file):
        cmd.extend(["--cookies", config.cookies_file])
        
    cmd.append(key)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "Failed to fetch metadata").strip())

    raw = json.loads(res.stdout)
    item = raw["entries"][0] if isinstance(raw, dict) and "entries" in raw and raw.get("entries") else raw

    preview = {
        "title": item.get("title"),
        "thumbnail": item.get("thumbnail"),
        "uploader": item.get("uploader"),
        "duration": item.get("duration"),
        "webpage_url": item.get("webpage_url") or key,
        "id": item.get("id"),
    }

    with preview_lock:
        preview_cache[key] = preview
        if len(preview_cache) > 200:
            preview_cache.clear()

    return preview


@app.post("/api/preview")
def api_preview():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    try:
        preview = get_preview(url)
        return jsonify({"ok": True, "preview": preview})
    except Exception as e:
        log.error(f"API Preview error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/scan")
def api_scan():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"ok": False, "error": "Invalid YouTube URL"}), 400

    ok = check_dependencies(install_whisper=False, skip_update_ytdlp=True, fatal=False)
    if not ok:
        return jsonify({"ok": False, "error": "FFmpeg not found"}), 400

    job_dir = os.path.join("clips", video_id)
    os.makedirs(job_dir, exist_ok=True)
    cache_file = os.path.join(job_dir, "segments.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data_cache = json.load(f)
                return jsonify({"ok": True, "video_id": video_id, "duration": data_cache.get("duration", 0), "segments": data_cache.get("segments", [])})
        except Exception:
            pass

    segments = fetch_most_replayed(video_id, config.min_score, config.max_duration)
    total = get_video_duration(video_id)
    
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"duration": total, "segments": segments}, f)
    except Exception:
        pass
        
    return jsonify({"ok": True, "video_id": video_id, "duration": total, "segments": segments})


@app.post("/api/clip")
def api_clip():
    payload = request.get_json(silent=True) or {}
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "created_at": now_ms(),
            "started_at": None,
            "finished_at": None,
            "error": None,
            "total": 0,
            "done": 0,
            "success": 0,
            "current": 0,
            "status_text": "",
            "stage": "",
            "stage_at": None,
            "stage_clip": 0,
            "subtitle_enabled": False,
            "outputs": [],
            "logs": [],
        }

    t = threading.Thread(target=run_job, args=(job_id, payload), daemon=True)
    t.start()
    return jsonify({"ok": True, "job_id": job_id})


@app.get("/api/job/<job_id>")
def api_job(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"ok": False, "error": "Job not found"}), 404
        return jsonify({"ok": True, "job": job})


@app.get("/clips/<job_id>/<path:filename>")
def serve_clip(job_id, filename):
    job_dir = os.path.join("clips", job_id)
    return send_from_directory(job_dir, filename, as_attachment=True)


@app.post("/api/cookies")
def api_cookies():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "No file selected"}), 400
    try:
        content = file.read().decode("utf-8")
        if not content.startswith("# Netscape HTTP Cookie File") and ".youtube.com" not in content:
             return jsonify({"ok": False, "error": "Invalid cookie format. Must be Netscape HTTP Cookie File."}), 400
             
        # Parse and ensure it's valid format
        valid_lines = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                valid_lines.append(line)
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                valid_lines.append(line)
                
        if len(valid_lines) < 2: # At least some comments + actual cookies
             return jsonify({"ok": False, "error": "No valid cookies found."}), 400
             
        with open("cookies.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(valid_lines))
            
        config.cookies_file = "cookies.txt"
        return jsonify({"ok": True, "message": "Cookies imported successfully"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.delete("/api/logs")
def clear_logs():
    try:
        log_dir = "logs"
        if os.path.isdir(log_dir):
            for filename in os.listdir(log_dir):
                if filename.endswith(".log"):
                    open(os.path.join(log_dir, filename), "w").close()
        return jsonify({"ok": True, "message": "Logs cleared"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/api/cookies/status")
def cookies_status():
    exists = False
    if config.cookies_file and os.path.exists(config.cookies_file):
        exists = True
    return jsonify({"ok": True, "exists": exists})

@app.post("/api/intro")
def upload_intro():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "No file selected"}), 400
    os.makedirs("assets", exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    path = os.path.join("assets", f"intro{ext}")
    file.save(path)
    config.intro_video = path
    return jsonify({"ok": True, "message": "Intro uploaded"})

@app.post("/api/outro")
def upload_outro():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "No file selected"}), 400
    os.makedirs("assets", exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    path = os.path.join("assets", f"outro{ext}")
    file.save(path)
    config.outro_video = path
    return jsonify({"ok": True, "message": "Outro uploaded"})

@app.get("/api/assets/status")
def assets_status():
    has_intro = bool(config.intro_video and os.path.exists(config.intro_video))
    has_outro = bool(config.outro_video and os.path.exists(config.outro_video))
    return jsonify({"ok": True, "has_intro": has_intro, "has_outro": has_outro})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
