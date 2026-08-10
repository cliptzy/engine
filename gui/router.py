import flet as ft
from gui.state import AppState, app_state
from gui.event_bus import event_bus
from gui import events
from gui.views.clipper_view import ClipperView
from gui.views.creator_hub_view import CreatorHubView
from gui.views.settings_view import SettingsView

class Router:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state
        self.current_route = ""

        self.content_container = ft.Container(expand=True)
        self.wrapper = ft.Container(content=self.content_container, expand=True)

        # Cache view instances agar state persistent saat navigasi
        self._view_cache: dict[str, ft.Control] = {}

        # Subscribe to state changes
        event_bus.subscribe(events.STATE_CHANGED, self.on_state_changed)

    def initialize(self) -> None:
        # Bersihkan cache saat reinitialize (misal setelah login ulang)
        self._view_cache.clear()
        self.navigate(self.state.current_page)

    def on_state_changed(self, state: AppState) -> None:
        if state.current_page != self.current_route:
            self.navigate(state.current_page)

    def _get_or_create_view(self, route: str) -> ft.Control:
        """Ambil view dari cache, atau buat baru jika belum ada."""
        if route not in self._view_cache:
            if route == "clipper":
                self._view_cache[route] = ClipperView(self.page)
            elif route == "creator_hub":
                self._view_cache[route] = CreatorHubView(on_video_select=self.handle_creator_hub_video_select)
            elif route == "settings":
                self._view_cache[route] = SettingsView(self.page)
            elif route == "debugger":
                from gui.views.debugger_view import DebuggerView
                self._view_cache[route] = DebuggerView(self.page)
            elif route == "logs":
                self._view_cache[route] = ft.Text("Logs View (To Be Implemented)", size=24)
            else:
                # Jangan cache unknown view
                return ft.Text("Unknown View", size=24)
        return self._view_cache[route]

    def handle_creator_hub_video_select(self, url: str) -> None:
        # Arahkan ke clipper view
        self.state.set_page("clipper")
        # trigger load video secara otomatis
        clipper_view = self._get_or_create_view("clipper")
        if isinstance(clipper_view, ClipperView):
            clipper_view.load_video_url(url)

    def navigate(self, route: str) -> None:
        self.current_route = route
        view = self._get_or_create_view(route)
        self.content_container.content = view
        self.page.update()
