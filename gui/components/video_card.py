import flet as ft
from typing import Optional, Callable, Any
from core.models import VideoInfo

class VideoCard(ft.Card):
    def __init__(
        self,
        video_info: VideoInfo,
        on_click: Optional[Callable[[Any], Any]] = None,
        **kwargs: Any
    ):
        super().__init__(**kwargs)
        self.video_info = video_info
        
        # Format duration
        mins = int(self.video_info.duration // 60)
        secs = int(self.video_info.duration % 60)
        duration_str = f"{mins}:{secs:02d}"
        
        # Create thumbnail image
        thumbnail: ft.Control
        if self.video_info.thumbnail_url:
            thumbnail = ft.Image(
                src=self.video_info.thumbnail_url,
                width=200,
                height=112,
                fit=ft.BoxFit.COVER,
                border_radius=8,
            )
        else:
            thumbnail = ft.Container(
                width=200,
                height=112,
                bgcolor="#313244",
                border_radius=8,
                content=ft.Icon(ft.Icons.VIDEO_FILE, size=40, color="#CDD6F4"),
            )
            
        def on_hover(e) -> None:
            e.control.scale = 1.05 if e.data == "true" else 1.0 # type: ignore
            e.control.update() # type: ignore
            
        self.content = ft.Container(
            width=200,
            on_click=on_click,
            on_hover=on_hover,
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            content=ft.Column(
                spacing=0,
                controls=[
                    thumbnail,
                    ft.Container(
                        padding=8,
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(
                                    self.video_info.title,
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    f"{duration_str} • {self.video_info.video_id}",
                                    size=12,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                )
                            ]
                        )
                    )
                ]
            )
        )
