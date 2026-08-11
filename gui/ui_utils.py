import flet as ft


def show_snackbar(page: ft.Page, message: str, error: bool = False) -> None:
    """
    Menampilkan SnackBar di layar Flet.

    Args:
        page (ft.Page): Referensi page aplikasi Flet
        message (str): Pesan yang ingin ditampilkan
        error (bool): Jika True, background merah. Jika False, background hijau.
    """
    bgcolor = ft.Colors.RED_700 if error else ft.Colors.GREEN_700
    sb = ft.SnackBar(ft.Text(message, color=ft.Colors.WHITE), bgcolor=bgcolor)
    sb.open = True
    page.overlay.append(sb)
    page.update()
