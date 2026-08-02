import os
import sys
import subprocess
import shutil
from typing import Optional, Callable
from core.logger import log
from core.config import config
from core.processing.utils import get_video_codec_args, run_command_with_logging

def generate_intro(index: int, metadata: dict, event_hook: Optional[Callable] = None) -> Optional[str]:
    intro_to_use = config.intro_video if (config.intro_video and os.path.isfile(config.intro_video)) else None
    
    if config.ai.use_generate_intro and metadata and metadata.get("highlight"):
        try:
            if callable(event_hook):
                event_hook("log", f"[intro] Generating AI Intro with TTS for clip {index}...")
            
            highlight_text = str(metadata.get("highlight", ""))
            
            # 1. Generate TTS using edge-tts
            tts_lang_config = getattr(config, "tts_language", "default")
            tts_gender = getattr(config, "tts_voice", "female")
            
            from core.utils import get_preview_data
            if tts_lang_config == "default":
                tts_lang = get_preview_data().get("language") or 'id'
            else:
                tts_lang = tts_lang_config
            
            voice_map = {
                "id": {"female": "id-ID-GadisNeural", "male": "id-ID-ArdiNeural"},
                "en": {"female": "en-US-JennyNeural", "male": "en-US-ChristopherNeural"},
                "es": {"female": "es-ES-ElviraNeural", "male": "es-MX-JorgeNeural"},
                "ja": {"female": "ja-JP-NanamiNeural", "male": "ja-JP-KeitaNeural"},
                "ko": {"female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"},
                "ms": {"female": "ms-MY-YasminNeural", "male": "ms-MY-OsmanNeural"}
            }
            
            base_lang = tts_lang.split("-")[0].lower() if tts_lang else "id"
            if base_lang not in voice_map:
                base_lang = "en"  # fallback
                
            voice = voice_map[base_lang].get(tts_gender.lower(), voice_map[base_lang]["female"])
            audio_path = os.path.join(config.job_dir, f"intro_audio_{index}.mp3")
            
            python_exe = sys.executable or "python"
            try:
                res = subprocess.run([
                    python_exe, "-m", "edge_tts", 
                    "--voice", voice,
                    "--rate=-15%",
                    "--text", highlight_text,
                    "--write-media", audio_path
                ], capture_output=True, text=True, check=True)
            except Exception as e:
                log.error(f"edge-tts failed: {e}")
                # Fallback to gTTS if edge-tts fails
                from gtts import gTTS
                tts = gTTS(text=highlight_text, lang=base_lang)
                tts.save(audio_path)
            
            # 2. Get duration
            try:
                res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], capture_output=True, text=True)
                duration_sec = float(res.stdout.strip())
            except:
                duration_sec = 3.0
            
            # 3. Create ASS for centered highlight text
            intro_ass = os.path.join(config.job_dir, f"intro_{index}.ass")
            from core.subtitle import format_ass_time
            end_ass = format_ass_time(duration_sec + 0.5) # add little padding
            
            with open(intro_ass, "w", encoding="utf-8") as f:
                f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n[V4+ Styles]\n")
                f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
                f.write(f"Style: Default,{config.subtitle.font},80,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,5,20,20,20,1\n\n")
                f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
                f.write(f"Dialogue: 0,0:00:00.00,{end_ass},Default,,0,0,0,,{{\\an5\\b1\\bord5\\3c&H000000&}}{highlight_text.upper()}\n")
            
            # 4. Generate black video with ASS and Audio
            intro_video_path = os.path.join(config.job_dir, f"intro_video_{index}.mp4")
            out_w, out_h = config.out_width or 720, config.out_height or 1280
            fontsdir_arg = ""
            if config.subtitle.fonts_dir and os.path.isdir(config.subtitle.fonts_dir):
                fontsdir_fwd = config.subtitle.fonts_dir.replace("\\", "/")
                fontsdir_arg = f":fontsdir='{fontsdir_fwd}'"
                
            intro_ass_fwd = intro_ass.replace("\\", "/")
            cmd_intro = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c=black:s={out_w}x{out_h}:d={duration_sec + 0.5}",
                "-i", audio_path,
                "-vf", f"subtitles=filename='{intro_ass_fwd}'{fontsdir_arg}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                intro_video_path
            ]
            subprocess.run(cmd_intro, check=True)
            intro_to_use = intro_video_path
            
        except Exception as e:
            log.error(f"Failed to generate intro video: {e}")
            if callable(event_hook):
                event_hook("log", f"[intro] ❌ Failed to generate intro: {e}")
                
    return intro_to_use

def stack_and_concat(
    current_clip: str,
    output_file: str,
    intro_to_use: Optional[str],
    index: int,
    event_hook: Optional[Callable] = None
) -> None:
    has_intro = intro_to_use and os.path.isfile(intro_to_use)
    has_outro = config.outro_video and os.path.isfile(config.outro_video)
    
    if has_intro or has_outro:
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "finalize", "clip_index": index})
                event_hook("log", f"[concat] Adding intro/outro to clip {index}...")
            except Exception:
                pass
                
        inputs = []
        filter_complex = ""
        input_idx = 0
        
        # Since videos might have different resolutions/codecs, we MUST re-encode and scale them to out_w x out_h
        out_w, out_h = config.out_width or 720, config.out_height or 1280
        scale_filter = f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        
        if has_intro:
            inputs.extend(["-i", intro_to_use])
            filter_complex += f"[{input_idx}:v:0]{scale_filter}[v{input_idx}]; [{input_idx}:a:0]aresample=async=1[a{input_idx}]; "
            input_idx += 1
            
        inputs.extend(["-i", current_clip])
        filter_complex += f"[{input_idx}:v:0]{scale_filter}[v{input_idx}]; [{input_idx}:a:0]aresample=async=1[a{input_idx}]; "
        input_idx += 1
        
        if has_outro:
            inputs.extend(["-i", config.outro_video])
            filter_complex += f"[{input_idx}:v:0]{scale_filter}[v{input_idx}]; [{input_idx}:a:0]aresample=async=1[a{input_idx}]; "
            input_idx += 1
            
        concat_parts = ""
        for i in range(input_idx):
            concat_parts += f"[v{i}][a{i}]"
        
        filter_complex += f"{concat_parts}concat=n={input_idx}:v=1:a=1[outv][outa]"
        
        cmd_concat = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "info"
        ] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[outa]",
        ] + get_video_codec_args() + [
            "-c:a", "aac", "-b:a", "128k",
            output_file
        ]
        
        run_command_with_logging(cmd_concat, event_hook, prefix="[ffmpeg-concat]")
    else:
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "finalize", "clip_index": index})
            except Exception:
                pass
        # Just copy the final result
        if current_clip != output_file:
            shutil.copy2(current_clip, output_file)
