#!/usr/bin/env python3
"""
PoC #5: Pengganti Fitur yang Tidak Ada di Flet
================================================
Verifikasi library pengganti:
1. pystray — System Tray icon (pengganti QSystemTrayIcon)
2. desktop-notifier — OS-level notifications (pengganti QSystemTrayIcon.showMessage)
3. Flet SnackBar — In-app notification fallback

Jalankan: python scripts/poc_flet_notifications.py
"""

import importlib
import sys


def check_pystray() -> dict:
    """Test pystray availability and basic creation."""
    result = {"name": "pystray (System Tray)", "available": False, "details": ""}

    try:
        import pystray
        from PIL import Image

        # Create a small test icon (16x16 solid purple)
        icon_image = Image.new("RGB", (16, 16), "#6C5CE7")

        # Verify we can create a menu
        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda: None),
            pystray.MenuItem("Quit", lambda: None),
        )

        # Verify icon creation (don't actually run it)
        icon = pystray.Icon("cliptzy_test", icon_image, "Cliptzy PoC", menu)

        result["available"] = True
        result["details"] = (
            f"v{getattr(pystray, '__version__', 'unknown')} — "
            f"Icon & Menu created successfully. "
            f"Backend: {type(icon).__module__}"
        )
    except ImportError:
        result["details"] = "NOT INSTALLED — install with: pip install pystray"
    except Exception as e:
        result["details"] = f"Error: {type(e).__name__}: {e}"

    return result


def check_desktop_notifier() -> dict:
    """Test desktop-notifier availability."""
    result = {
        "name": "desktop-notifier (OS Notifications)",
        "available": False,
        "details": "",
    }

    try:
        from desktop_notifier import DesktopNotifier, Urgency

        notifier = DesktopNotifier(app_name="Cliptzy PoC")

        result["available"] = True
        result["details"] = (
            f"DesktopNotifier created successfully. "
            f"Urgency levels: {[u.name for u in Urgency]}"
        )
    except ImportError:
        result["details"] = "NOT INSTALLED — install with: pip install desktop-notifier"
    except Exception as e:
        result["details"] = f"Error: {type(e).__name__}: {e}"

    return result


def check_flet_snackbar() -> dict:
    """Test Flet SnackBar availability (in-app fallback)."""
    result = {
        "name": "Flet SnackBar (In-app Notification)",
        "available": False,
        "details": "",
    }

    try:
        import flet as ft

        snack = ft.SnackBar(
            content=ft.Text("Test notification"),
            action="Dismiss",
            duration=3000,
        )

        result["available"] = True
        result["details"] = f"SnackBar control available in Flet v{ft.version.version}"
    except ImportError:
        result["details"] = "Flet not installed"
    except Exception as e:
        result["details"] = f"Error: {type(e).__name__}: {e}"

    return result


def main() -> None:
    print("=" * 70)
    print("🔬 PoC #5: Flet Missing Features — Replacement Library Audit")
    print("=" * 70)

    checks = [
        check_pystray(),
        check_desktop_notifier(),
        check_flet_snackbar(),
    ]

    for check in checks:
        status = "✅" if check["available"] else "❌"
        print(f"\n{status} {check['name']}")
        print(f"   {check['details']}")

    print("\n" + "=" * 70)

    available_count = sum(1 for c in checks if c["available"])
    total = len(checks)

    if available_count == total:
        print(f"🎉 ALL {total} REPLACEMENT LIBRARIES AVAILABLE!")
    else:
        missing = [c["name"] for c in checks if not c["available"]]
        print(f"⚠️ {len(missing)} library missing: {', '.join(missing)}")
        print("\nTo install missing libraries:")
        if not checks[0]["available"]:
            print("  python scripts/manage_reqs.py add 'pystray'")
        if not checks[1]["available"]:
            print("  python scripts/manage_reqs.py add 'desktop-notifier'")

    print("=" * 70)


if __name__ == "__main__":
    main()
