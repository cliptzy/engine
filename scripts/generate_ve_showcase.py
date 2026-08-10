import os
import sys
import subprocess
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.logger import log
from core.video_effects import video_effect_manager

def generate_ve_showcase(input_file: str, output_file: str):
    if not os.path.exists(input_file):
        log.error(f"Input file not found: {input_file}")
        return False
        
    effects_to_test = []
    
    # Collect all effects
    for emo, effects in video_effect_manager.effects_map.items():
        for eff in effects:
            effects_to_test.append((emo, eff))
            
    if not effects_to_test:
        log.warning("No video effects found in video_effects.json")
        return False
        
    log.info(f"Generating showcase for {len(effects_to_test)} video effects...")
    
    # We will allocate 4 seconds for each effect.
    total_duration = len(effects_to_test) * 4
    
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
        "-stream_loop", "-1", "-i", input_file
    ]
    
    ve_input_offset = 1
    for emo, eff in effects_to_test:
        eff_path = os.path.join("assets", "video_effects", eff["file"])
        if os.path.exists(eff_path):
            cmd.extend(["-i", eff_path])
        else:
            log.warning(f"Missing file for effect {eff.get('name')}: {eff_path}")
            
    fc_parts = []
    out_w, out_h = 720, 1280
    
    # Font path setup for drawtext
    font_arg = ""
    if sys.platform == "win32":
        font_paths = ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/consola.ttf"]
    elif sys.platform == "darwin":
        font_paths = ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ]
    for fp in font_paths:
        if os.path.exists(fp):
            fp_esc = fp.replace(":", "\\:")
            font_arg = f"fontfile='{fp_esc}':"
            break
            
    last_v = "[0:v]"
    a_mix_inputs = "[0:a]"
    a_mix_count = 1
    
    valid_eff_index = 0
    for i, (emo, eff) in enumerate(effects_to_test):
        eff_path = os.path.join("assets", "video_effects", eff["file"])
        if not os.path.exists(eff_path):
            continue
            
        ve_idx = ve_input_offset + valid_eff_index
        start_time = i * 4
        
        processed_v = f"[ve_v_{i}]"
        v_type = eff.get("type", "greenscreen")
        if v_type == "greenscreen":
            key_col = eff.get("key_color", "0x00FF00")
            fc_parts.append(f"[{ve_idx}:v]scale={out_w}:-1,chromakey={key_col}:0.1:0.1,setpts=PTS-STARTPTS+{start_time}/TB{processed_v}")
        elif v_type == "alpha":
            fc_parts.append(f"[{ve_idx}:v]scale={out_w}:-1,setpts=PTS-STARTPTS+{start_time}/TB{processed_v}")
        else:
            fc_parts.append(f"[{ve_idx}:v]scale={out_w}:{out_h},setpts=PTS-STARTPTS+{start_time}/TB{processed_v}")
            
        pos_y = "(H-h)/2"
        if eff.get("position") == "bottom":
            pos_y = "H-h-50"
        elif eff.get("position") == "top":
            pos_y = "50"
            
        # Draw text label without colons
        label = f"Emotion - {emo.upper()} | Name - {eff.get('name', 'Unknown')}"
        label_v = f"[lbl_v_{i}]"
        fc_parts.append(f"{processed_v}drawtext={font_arg}text='{label}':x=(w-text_w)/2:y=100:fontcolor=white:fontsize=36:box=1:boxcolor=black@0.6:boxborderw=10{label_v}")
            
        next_v = f"[vout_{i+1}]"
        fc_parts.append(f"{last_v}{label_v}overlay=x=(W-w)/2:y={pos_y}:enable='between(t,{start_time},{start_time+4})':eof_action=pass{next_v}")
        last_v = next_v
        
        delay_ms = start_time * 1000
        ve_a = f"[ve_a_{i}]"
        fc_parts.append(f"[{ve_idx}:a]adelay={delay_ms}|{delay_ms}{ve_a}")
        a_mix_inputs += ve_a
        a_mix_count += 1
        
        valid_eff_index += 1
        
    fc_parts.append(f"{last_v}format=yuv420p[vout_final]")
    fc_parts.append(f"{a_mix_inputs}amix=inputs={a_mix_count}:duration=first:dropout_transition=0:normalize=0[aout]")
    
    cmd.extend(["-filter_complex", ";".join(fc_parts)])
    cmd.extend(["-map", "[vout_final]", "-map", "[aout]"])
    cmd.extend(["-t", str(total_duration)])
    cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "128k"])
    cmd.append(output_file)
    
    log.info(f"Running showcase generation to {output_file}...")
    try:
        subprocess.run(cmd, check=True)
        log.info("Showcase generated successfully.")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Failed to generate showcase: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_ve_showcase.py <input_video.mp4> <output_video.mp4>")
        sys.exit(1)
    generate_ve_showcase(sys.argv[1], sys.argv[2])
