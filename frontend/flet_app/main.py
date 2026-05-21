import flet as ft

from app.shell import AppShell


def main(page: ft.Page) -> None:
    AppShell(page).run()


if __name__ == "__main__":
    ft.run(main)
