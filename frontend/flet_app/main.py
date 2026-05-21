import flet as ft

from app.shell import AppShell


def main(page: ft.Page) -> None:
    AppShell(page).run()


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
