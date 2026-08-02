import flet as ft
from typing import Optional, Callable, Any, cast

class SpinBox(ft.Row):
    def __init__(
        self,
        value: int = 0,
        min_value: int = 0,
        max_value: int = 100,
        step: int = 1,
        width: int = 240,
        label: Optional[str] = None,
        on_change: Optional[Callable[[Any], Any]] = None,
        **kwargs: Any
    ):
        super().__init__(**kwargs)
        self.alignment = ft.MainAxisAlignment.START
        
        self._value = value
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self._width = width
        self._on_change_callback = on_change
        
        self.text_field = ft.TextField(
            value=str(self._value),
            text_align=ft.TextAlign.CENTER,
            width=self._width - 80,
            on_change=self._text_changed,
            label=label,
        )
        
        self.controls = cast(list[ft.Control], [
            ft.IconButton(ft.Icons.REMOVE, on_click=self._minus_click),
            self.text_field,
            ft.IconButton(ft.Icons.ADD, on_click=self._plus_click),
        ])

    def _update_value(self, new_value: int, e: Optional[Any] = None) -> None:
        if new_value < self.min_value:
            new_value = self.min_value
        elif new_value > self.max_value:
            new_value = self.max_value
            
        self._value = new_value
        self.text_field.value = str(self._value)
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass
        if self._on_change_callback and e:
            self._on_change_callback(e)

    def _minus_click(self, e: Any) -> None:
        self._update_value(self._value - self.step, e)

    def _plus_click(self, e: Any) -> None:
        self._update_value(self._value + self.step, e)
        
    def _text_changed(self, e: Any) -> None:
        try:
            val = int(self.text_field.value) if self.text_field.value else 0
            self._update_value(val, e)
        except ValueError:
            self.text_field.value = str(self._value)
            try:
                if self.page: self.page.update()
                else: self.update()
            except Exception:
                pass
    @property
    def value(self) -> int:
        return self._value
        
    @value.setter
    def value(self, val: int) -> None:
        self._update_value(val)
