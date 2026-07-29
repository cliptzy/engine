from typing import Tuple, Optional
import os

def escape_subtitles_filter_path(path: str) -> str:
    """Escapes file paths for use in FFmpeg subtitles filter."""
    abs_path = os.path.abspath(path)
    return abs_path.replace("\\", "/").replace(":", "\\:")

def build_subtitle_force_style(font: str, location: str) -> str:
    """Builds the force_style string for FFmpeg subtitles filter."""
    alignment = "2" if location == "bottom" else "5"
    margin_v = "40" if location == "bottom" else "0"
    return (
        f"FontName={font},FontSize=12,Bold=1,"
        f"PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
        f"BorderStyle=1,Outline=2,Shadow=1,"
        f"Alignment={alignment},MarginV={margin_v}"
    )

def build_cover_scale_crop_vf(out_w: int, out_h: int) -> str:
    """Builds a video filter string for scaling and center-cropping to fill dimensions."""
    ar_expr = f"{out_w}/{out_h}"
    scale = f"scale='if(gte(iw/ih,{ar_expr}),-2,{out_w})':'if(gte(iw/ih,{ar_expr}),{out_h},-2)'"
    crop = f"crop={out_w}:{out_h}:(iw-{out_w})/2:(ih-{out_h})/2"
    return f"{scale},{crop}"

def build_cover_scale_vf(out_w: int, out_h: int) -> str:
    """Builds a video filter string for scaling to fill dimensions."""
    ar_expr = f"{out_w}/{out_h}"
    scale = f"scale='if(gte(iw/ih,{ar_expr}),-2,{out_w})':'if(gte(iw/ih,{ar_expr}),{out_h},-2)'"
    return scale

def get_split_heights(out_h: Optional[int], bottom_height: int) -> Tuple[Optional[int], Optional[int]]:
    """Calculates the top and bottom heights for split screen crop mode."""
    if not out_h:
        return None, None
    bottom = min(bottom_height, max(1, out_h - 1))
    top = max(1, out_h - bottom)
    return top, bottom
