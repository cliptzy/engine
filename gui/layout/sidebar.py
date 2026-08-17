import flet as ft


class Sidebar(ft.NavigationRail):
    def __init__(self, on_navigate):
        super().__init__()
        self.selected_index = 0
        self.label_type = ft.NavigationRailLabelType.ALL
        self.min_width = 100
        self.min_extended_width = 200
        self.group_alignment = -0.9
        self.bgcolor = ft.Colors.TRANSPARENT

        self.destinations = [
            ft.NavigationRailDestination(
                icon=ft.Icons.VIDEO_FILE_OUTLINED,  # type: ignore
                selected_icon=ft.Icons.VIDEO_FILE,  # type: ignore
                label="Clipper",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.EXPLORE_OUTLINED,  # type: ignore
                selected_icon=ft.Icons.EXPLORE,  # type: ignore
                label="Creator Hub",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,  # type: ignore
                selected_icon=ft.Icons.SETTINGS,  # type: ignore
                label="Settings",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.PSYCHOLOGY_OUTLINED,  # type: ignore
                selected_icon=ft.Icons.PSYCHOLOGY,  # type: ignore
                label="Brainrot",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.BUG_REPORT_OUTLINED,  # type: ignore
                selected_icon=ft.Icons.BUG_REPORT,  # type: ignore
                label="Debugger",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.INFO_OUTLINE,  # type: ignore
                selected_icon=ft.Icons.INFO,  # type: ignore
                label="About",
            ),
        ]

        self.on_change = lambda e: on_navigate(e.control.selected_index)  # type: ignore
