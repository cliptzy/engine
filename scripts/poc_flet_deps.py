#!/usr/bin/env python3
"""
PoC #2: Dependency Compatibility Audit
=======================================
Verifikasi bahwa semua dependensi kritis Cliptzy dapat di-import
bersama Flet tanpa konflik dalam satu environment.
"""

import importlib
import sys
import time

# Daftar dependensi kritis yang harus kompatibel
CRITICAL_DEPS: list[tuple[str, str]] = [
    # (import_name, display_name)
    ("flet", "Flet (GUI Framework baru)"),
    ("yt_dlp", "yt-dlp (YouTube downloader)"),
    ("faster_whisper", "faster-whisper (Speech recognition)"),
    ("cv2", "OpenCV (Face detection)"),
    ("PIL", "Pillow (Image processing)"),
    ("edge_tts", "edge-tts (Text-to-speech)"),
    ("requests", "Requests (HTTP client)"),
    ("openai", "OpenAI (AI provider)"),
    ("google.genai", "Google GenAI (AI provider)"),
    ("supabase", "Supabase (Backend auth)"),
    ("dotenv", "python-dotenv (Env vars)"),
    ("psutil", "psutil (System monitoring)"),
]

OPTIONAL_DEPS: list[tuple[str, str]] = [
    ("instagrapi", "Instagrapi (Instagram uploader)"),
    ("playwright", "Playwright (Browser automation)"),
    ("googleapiclient", "Google API Client (YouTube API)"),
    ("google_auth_oauthlib", "Google Auth OAuth (OAuth2)"),
    ("gtts", "gTTS (Google TTS)"),
]


def check_import(module_name: str, display_name: str) -> tuple[bool, str]:
    """Attempt to import a module and return status."""
    start = time.perf_counter()
    try:
        mod = importlib.import_module(module_name)
        elapsed = time.perf_counter() - start
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "unknown"))
        return True, f"✅ {display_name}: v{version} ({elapsed:.2f}s)"
    except ImportError as e:
        return False, f"❌ {display_name}: ImportError — {e}"
    except Exception as e:
        return False, f"⚠️ {display_name}: {type(e).__name__} — {e}"


def main() -> None:
    print("=" * 70)
    print("🔬 Cliptzy Dependency Compatibility Audit")
    print(f"   Python {sys.version}")
    print(f"   Executable: {sys.executable}")
    print("=" * 70)

    total_pass = 0
    total_fail = 0

    print("\n📦 Critical Dependencies:")
    print("-" * 50)
    for module_name, display_name in CRITICAL_DEPS:
        success, message = check_import(module_name, display_name)
        print(f"  {message}")
        if success:
            total_pass += 1
        else:
            total_fail += 1

    print("\n📦 Optional Dependencies:")
    print("-" * 50)
    opt_pass = 0
    opt_fail = 0
    for module_name, display_name in OPTIONAL_DEPS:
        success, message = check_import(module_name, display_name)
        print(f"  {message}")
        if success:
            opt_pass += 1
        else:
            opt_fail += 1

    # Flet-specific checks
    print("\n🧪 Flet-Specific Feature Checks:")
    print("-" * 50)

    try:
        import flet as ft

        # Check Video control (in flet_video package)
        try:
            from flet_video import Video, VideoMedia

            print("  ✅ flet_video.Video control available")
            total_pass += 1
        except ImportError:
            print("  ❌ flet_video.Video NOT available (install flet-video)")
            total_fail += 1

        # Check NavigationRail exists
        assert hasattr(ft, "NavigationRail"), "ft.NavigationRail not found"
        print("  ✅ ft.NavigationRail control available")
        total_pass += 1

        # Check FilePicker exists
        assert hasattr(ft, "FilePicker"), "ft.FilePicker not found"
        print("  ✅ ft.FilePicker control available")
        total_pass += 1

        # Check ProgressBar exists
        assert hasattr(ft, "ProgressBar"), "ft.ProgressBar not found"
        print("  ✅ ft.ProgressBar control available")
        total_pass += 1

        # Check Tabs exists
        assert hasattr(ft, "Tabs"), "ft.Tabs not found"
        print("  ✅ ft.Tabs control available")
        total_pass += 1

        # Check AlertDialog exists
        assert hasattr(ft, "AlertDialog"), "ft.AlertDialog not found"
        print("  ✅ ft.AlertDialog control available")
        total_pass += 1

        # Check theming
        theme = ft.Theme(color_scheme_seed=ft.Colors.DEEP_PURPLE)
        assert theme is not None, "Theme creation failed"
        print("  ✅ ft.Theme creation works")
        total_pass += 1

        # Check replacement libraries
        try:
            import pystray

            print("  ✅ pystray (System Tray replacement) available")
            total_pass += 1
        except ImportError:
            print("  ❌ pystray NOT available")
            total_fail += 1

        try:
            from desktop_notifier import DesktopNotifier

            print("  ✅ desktop-notifier (Notification replacement) available")
            total_pass += 1
        except ImportError:
            print("  ❌ desktop-notifier NOT available")
            total_fail += 1

        # Print Flet version
        print(f"\n  ℹ️  Flet version: {ft.__version__}")

    except Exception as e:
        print(f"  ❌ Flet feature check failed: {e}")
        total_fail += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"📊 SUMMARY")
    print(f"   Critical: {total_pass} passed, {total_fail} failed")
    print(f"   Optional: {opt_pass} passed, {opt_fail} failed")

    if total_fail == 0:
        print("\n🎉 ALL CRITICAL DEPENDENCIES COMPATIBLE WITH FLET!")
    else:
        print(f"\n⚠️ {total_fail} CRITICAL DEPENDENCY ISSUE(S) DETECTED")
        print("   Review failures above before proceeding with migration.")

    print("=" * 70)
    sys.exit(total_fail)


if __name__ == "__main__":
    main()
