import flet as ft

def build_theme() -> ft.Theme:
    """Build and return the Material Design theme for Cliptzy."""
    return ft.Theme(
        font_family="Inter",
        color_scheme_seed=ft.Colors.DEEP_PURPLE,
        color_scheme=ft.ColorScheme(
            primary="#6C5CE7",
            on_primary="#FFFFFF",
            secondary="#00B894",
            error="#FF7675",
            surface="#1E1E2E",
            on_surface="#CDD6F4"
        ),
        # page_transitions=ft.PageTransitionsTheme(
        #     windows=ft.PageTransitionTheme.FADE_UPWARDS,
        #     macos=ft.PageTransitionTheme.FADE_UPWARDS,
        #     linux=ft.PageTransitionTheme.FADE_UPWARDS,
        # )
    )
