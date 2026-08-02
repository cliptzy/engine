import flet as ft
from typing import Any

class ProgressIndicator(ft.Column):
    def __init__(
        self,
        label: str = "",
        value: float = 0.0,
        **kwargs: Any
    ):
        super().__init__(**kwargs)
        self.spacing = 8
        
        self.label_text = ft.Text(value=label, size=14, weight=ft.FontWeight.W_500)
        self.progress_bar = ft.ProgressBar(value=value, color="#6C5CE7", bgcolor="#313244")
        self.progress_bar.animate = ft.Animation(300, ft.AnimationCurve.EASE_OUT) # type: ignore
        
        self.controls = [
            self.label_text,
            self.progress_bar,
        ]

    @property
    def value(self) -> float:
        # type: ignore
        return self.progress_bar.value or 0.0
        
    @value.setter
    def value(self, val: float) -> None:
        self.progress_bar.value = val
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass
    @property
    def label(self) -> str:
        # type: ignore
        return self.label_text.value or ""
        
    @label.setter
    def label(self, val: str) -> None:
        self.label_text.value = val
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass