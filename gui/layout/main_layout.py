import flet as ft

from gui.layout.header import Header
from gui.layout.sidebar import Sidebar


class MainLayout(ft.Row):
    def __init__(self, sidebar: Sidebar, content_area: ft.Container):
        super().__init__()

        main_area = ft.Container(
            content=content_area,
            padding=ft.Padding.all(10),
            border_radius=12,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            expand=True,
        )

        self.expand = True
        self.controls = [
            sidebar,
            # ft.VerticalDivider(width=1),
            main_area,
        ]
