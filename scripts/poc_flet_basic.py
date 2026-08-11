#!/usr/bin/env python3
"""
PoC #1: Flet Basic App Launch & Controls Verification
=====================================================
Verifikasi bahwa Flet dapat diluncurkan dengan benar di environment ini.
Menguji: Page, NavigationRail, TextField, Dropdown, Checkbox, ProgressBar,
         Slider, AlertDialog, FilePicker, Tabs, dark theme.
"""

import flet as ft


def main(page: ft.Page) -> None:
    page.title = "Cliptzy Flet PoC #1 — Basic Controls"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.DEEP_PURPLE,
        color_scheme=ft.ColorScheme(
            primary="#6C5CE7",
            secondary="#00B894",
            error="#FF7675",
            surface="#1E1E2E",
            on_surface="#CDD6F4",
        ),
    )
    page.window.width = 1000
    page.window.height = 700

    # --- State ---
    results: list[str] = []

    def log_result(test_name: str, status: str = "✅ PASS") -> None:
        msg = f"{status} {test_name}"
        results.append(msg)
        result_text.value = "\n".join(results)
        page.update()

    # --- Result display ---
    result_text = ft.Text(
        value="Running PoC tests...\n",
        selectable=True,
        size=13,
        font_family="monospace",
    )

    # --- Test 1: TextField ---
    text_field = ft.TextField(
        label="Test Input",
        hint_text="Type something...",
        on_change=lambda e: log_result(f"TextField on_change: '{e.control.value}'"),  # type: ignore
    )
    log_result("TextField created")

    # --- Test 2: Dropdown ---
    dropdown = ft.Dropdown(
        label="Crop Mode",
        options=[
            ft.dropdown.Option("default", "Default (Center Crop)"),
            ft.dropdown.Option("split_left", "Split Left"),
            ft.dropdown.Option("split_right", "Split Right"),
        ],
        value="default",
        on_select=lambda e: log_result(f"Dropdown selected: {e.control.value}"),  # type: ignore
    )
    log_result("Dropdown created")

    # --- Test 3: Checkbox ---
    checkbox = ft.Checkbox(
        label="Enable Subtitles",
        value=True,
        on_change=lambda e: log_result(f"Checkbox: {e.control.value}"),  # type: ignore
    )
    log_result("Checkbox created")

    # --- Test 4: ProgressBar ---
    progress = ft.ProgressBar(value=0.65, color="#6C5CE7", bgcolor="#313244")
    log_result("ProgressBar created (value=0.65)")

    # --- Test 5: Slider ---
    slider = ft.Slider(
        min=0,
        max=100,
        value=50,
        divisions=100,
        label="{value}%",
        on_change=lambda e: log_result(f"Slider: {e.control.value:.0f}%"),  # type: ignore
    )
    log_result("Slider created")

    # --- Test 6: Tabs ---
    tabs = ft.Tabs(
        length=3,
        selected_index=0,
        content=ft.TabBar(
            tabs=[
                ft.Tab(label="YouTube"),
                ft.Tab(label="TikTok"),
                ft.Tab(label="Instagram"),
            ]
        ),
        on_change=lambda e: log_result(f"Tab selected: {e.control.selected_index}"),  # type: ignore
    )
    log_result("Tabs created")

    # --- Test 7: AlertDialog ---
    def close_dlg(e):
        dialog.open = False
        page.update()

    def show_dialog(e) -> None:
        global dialog
        dialog = ft.AlertDialog(
            title=ft.Text("Confirmation"),
            content=ft.Text("Are you sure you want to proceed?"),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.Button(
                    "OK",
                    on_click=lambda _: (
                        log_result("AlertDialog: OK clicked"),
                        close_dlg(None),
                    ),
                ),
            ],
            modal=True,
        )
        page.show_dialog(dialog)
        log_result("AlertDialog opened")

    dialog_btn = ft.Button(
        "Test AlertDialog", icon=ft.Icons.WARNING, on_click=show_dialog
    )

    # --- Test 8: FilePicker ---
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    async def open_picker(e) -> None:
        files = await file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["mp4", "mkv", "txt"],
        )
        if files:
            for f in files:
                log_result(f"FilePicker: {f.name} ({f.size} bytes)")
        else:
            log_result("FilePicker: cancelled")

    pick_btn = ft.Button(
        "Test FilePicker",
        icon=ft.Icons.UPLOAD_FILE,
        on_click=open_picker,
    )

    # --- Test 9: Custom SpinBox (proof of concept) ---
    spin_value = ft.TextField(
        value="10",
        width=80,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    def spin_change(delta: int) -> None:
        current = int(spin_value.value or "0")
        spin_value.value = str(current + delta)
        log_result(f"SpinBox: {spin_value.value}")
        page.update()

    spin_box = ft.Row(
        controls=[
            ft.IconButton(ft.Icons.REMOVE, on_click=lambda _: spin_change(-1)),
            spin_value,
            ft.IconButton(ft.Icons.ADD, on_click=lambda _: spin_change(1)),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    log_result("Custom SpinBox created")

    # --- Navigation Rail ---
    nav_pages = {
        0: "Dashboard",
        1: "Settings",
        2: "Results",
    }

    def on_nav_change(e) -> None:
        idx = e.control.selected_index  # type: ignore
        log_result(f"NavigationRail: page {nav_pages.get(idx, idx)}")

    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="Dashboard"),
            ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Settings"),
            ft.NavigationRailDestination(icon=ft.Icons.CHECK_CIRCLE, label="Results"),
        ],
        on_change=on_nav_change,
    )
    log_result("NavigationRail created")

    # --- Layout ---
    controls_column = ft.Column(
        controls=[
            ft.Text("🧪 Flet Controls PoC", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            text_field,
            dropdown,
            checkbox,
            ft.Text("ProgressBar (65%):"),
            progress,
            ft.Text("Slider:"),
            slider,
            tabs,
            ft.Row([dialog_btn, pick_btn]),
            ft.Text("Custom SpinBox:"),
            spin_box,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=12,
    )

    result_column = ft.Column(
        controls=[
            ft.Text(
                "📋 Test Results",
                size=16,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Divider(),
            ft.Container(
                content=result_text,
                bgcolor="#11111B",
                padding=12,
                border_radius=8,
                expand=True,
            ),
        ],
        expand=True,
    )

    page.add(
        ft.Row(
            controls=[
                nav_rail,
                ft.VerticalDivider(width=1),
                ft.Container(content=controls_column, expand=2, padding=20),
                ft.VerticalDivider(width=1),
                ft.Container(content=result_column, expand=1, padding=20),
            ],
            expand=True,
        )
    )

    log_result("=== All controls initialized successfully ===", "🎉")


if __name__ == "__main__":
    ft.run(main)
