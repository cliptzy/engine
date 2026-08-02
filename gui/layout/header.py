import flet as ft

class Header(ft.AppBar):
    def __init__(self):
        super().__init__()
        self.title = ft.Text("Cliptzy", weight=ft.FontWeight.BOLD)
        self.center_title = False
        self.elevation = 0
        self.bgcolor = "#1E1E2E"
        self.refresh_profile()
        
    def refresh_profile(self) -> None:
        from core.supabase_sync import supabase_sync
        user = supabase_sync.user
        
        profile_control = None
        if user and hasattr(user, "user_metadata") and user.user_metadata:
            avatar_url = user.user_metadata.get("avatar_url") or user.user_metadata.get("picture")
            full_name = user.user_metadata.get("full_name") or user.user_metadata.get("name") or "User Profile"
            if avatar_url:
                profile_control = ft.Container(
                    content=ft.Image(
                        src=avatar_url,
                        width=32,
                        height=32,
                        border_radius=16,
                        fit=ft.BoxFit.COVER
                    ),
                    tooltip=full_name,
                    margin=ft.margin.Margin(right=10)
                )
        
        if not profile_control:
            profile_control = ft.IconButton(
                icon=ft.Icons.ACCOUNT_CIRCLE,
                tooltip="Profil Pengguna",
                margin=ft.margin.Margin(right=10)
            )
            
        import typing
        self.actions = typing.cast(list[ft.Control], [
            profile_control,
            ft.Container(width=10)
        ])
