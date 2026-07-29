import argparse
import os
import sys

from core import (
    config,
    log,
    check_dependencies,
    is_ffmpeg_available,
    get_model_size,
    extract_video_id,
    fetch_most_replayed,
    get_video_duration,
    process_single_clip
)

def parse_args():
    parser = argparse.ArgumentParser(prog="yt-heatmap-clipper", description="YouTube Heatmap Clipper CLI")
    parser.add_argument("--url", help="YouTube URL (watch/shorts/youtu.be)")
    parser.add_argument(
        "--crop",
        choices=["default", "split_left", "split_right"],
        help="Crop mode",
    )
    parser.add_argument(
        "--subtitle",
        choices=["y", "n"],
        help="Enable auto subtitle (y/n)",
    )
    parser.add_argument("--whisper-model", dest="whisper_model", help="Faster-Whisper model")
    parser.add_argument("--subtitle-font", dest="subtitle_font", help="Subtitle font name (e.g., Poppins)")
    parser.add_argument("--subtitle-fontsdir", dest="subtitle_fontsdir", help="Folder containing .ttf/.otf fonts")
    parser.add_argument(
        "--subtitle-location",
        dest="subtitle_location",
        choices=["center", "bottom"],
        help="Subtitle placement: center or bottom",
    )
    parser.add_argument("--ratio", choices=["9:16", "1:1", "16:9", "original"], help="Output ratio preset")
    parser.add_argument("--check", action="store_true", help="Check dependencies then exit")
    parser.add_argument("--no-update-ytdlp", action="store_true", help="Skip auto-update yt-dlp")
    return parser.parse_args()

def main():
    args = parse_args()

    # Apply configuration from arguments
    if args.whisper_model:
        config.whisper_model = args.whisper_model
    if args.subtitle_font:
        config.subtitle_font = args.subtitle_font
    if args.subtitle_fontsdir:
        config.subtitle_fonts_dir = args.subtitle_fontsdir
    if args.subtitle_location:
        config.subtitle_location = args.subtitle_location
    if args.ratio:
        config.set_ratio_preset(args.ratio)

    if args.check:
        check_dependencies(install_whisper=False, skip_update_ytdlp=args.no_update_ytdlp)
        log.info("Basic dependencies OK.")
        return

    if not is_ffmpeg_available():
        check_dependencies(install_whisper=False, skip_update_ytdlp=args.no_update_ytdlp, fatal=False)
        if not is_ffmpeg_available():
            log.error("FFmpeg not found. Please install FFmpeg and ensure it is in PATH.")
            return

    crop_mode = args.crop
    crop_desc = None
    if crop_mode:
        crop_desc = {
            "default": "Default center crop",
            "split_left": "Split crop (bottom-left facecam)",
            "split_right": "Split crop (bottom-right facecam)",
        }[crop_mode]

    subtitle_choice = args.subtitle
    use_subtitle = subtitle_choice == "y" if subtitle_choice else None
    link = args.url

    # Interactive prompt if arguments are missing
    if crop_mode is None or use_subtitle is None or not link:
        print("\n=== Crop Mode ===")
        print("1. Default (center crop)")
        print("2. Split 1 (top: center, bottom: bottom-left (facecam))")
        print("3. Split 2 (top: center, bottom: bottom-right (facecam))")

        while crop_mode is None:
            choice = input("\nSelect crop mode (1-3): ").strip()
            if choice == "1":
                crop_mode = "default"
                crop_desc = "Default center crop"
                break
            elif choice == "2":
                crop_mode = "split_left"
                crop_desc = "Split crop (bottom-left facecam)"
                break
            elif choice == "3":
                crop_mode = "split_right"
                crop_desc = "Split crop (bottom-right facecam)"
                break
            print("Invalid choice. Please enter 1, 2, or 3.")

        print(f"Selected: {crop_desc}")
        print("\n=== Auto Subtitle ===")
        print(f"Available model: {config.whisper_model} (~{get_model_size(config.whisper_model)})")
        
        while use_subtitle is None:
            sub_choice = input("Add auto subtitle using Faster-Whisper? (y/n): ").strip().lower()
            if sub_choice in ["y", "yes"]:
                use_subtitle = True
            elif sub_choice in ["n", "no"]:
                use_subtitle = False
            else:
                print("Invalid choice. Please enter y or n.")

        if use_subtitle:
            print(f"Subtitle enabled (Model: {config.whisper_model}, Language: id)")
        else:
            print("Subtitle disabled")
        print()

        check_dependencies(install_whisper=use_subtitle, skip_update_ytdlp=args.no_update_ytdlp)

        if not link:
            link = input("YouTube Link: ").strip()
    else:
        check_dependencies(install_whisper=use_subtitle, skip_update_ytdlp=args.no_update_ytdlp)

    video_id = extract_video_id(link)
    if not video_id:
        log.error("Invalid YouTube link.")
        return

    heatmap_data = fetch_most_replayed(video_id, config.min_score, config.max_duration)
    if not heatmap_data:
        log.warning("No high-engagement segments found.")
        return

    log.info(f"Found {len(heatmap_data)} high-engagement segments.")
    total_duration = get_video_duration(video_id)
    
    os.makedirs(config.output_dir, exist_ok=True)
    
    log.info(f"Processing clips with {config.padding}s pre-padding and {config.padding}s post-padding.")
    log.info(f"Using crop mode: {crop_desc}")

    success_count = 0
    for index, item in enumerate(heatmap_data, start=1):
        if success_count >= config.max_clips:
            break

        if process_single_clip(
            video_id=video_id,
            item=item,
            index=index,
            total_duration=total_duration,
            crop_mode=crop_mode,
            use_subtitle=use_subtitle
        ):
            success_count += 1

    log.info(f"Finished processing. Successfully created {success_count} clips.")

if __name__ == "__main__":
    main()
