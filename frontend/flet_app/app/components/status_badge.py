import flet as ft


def status_badge(value: str | None) -> ft.Control:
    text = value or "Sin estado"
    normalized = text.upper()
    color = ft.Colors.BLUE_GREY_100
    text_color = ft.Colors.BLUE_GREY_900

    if normalized in {"ACTIVA", "ACTIVO", "CONFIRMADA", "VIGENTE"}:
        color = ft.Colors.GREEN_100
        text_color = ft.Colors.GREEN_900
    elif normalized in {"BAJA", "INACTIVA", "CANCELADA", "ANULADA"}:
        color = ft.Colors.RED_100
        text_color = ft.Colors.RED_900
    elif normalized in {"BORRADOR", "PENDIENTE"}:
        color = ft.Colors.AMBER_100
        text_color = ft.Colors.AMBER_900

    return ft.Container(
        content=ft.Text(text, size=12, color=text_color),
        bgcolor=color,
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )
