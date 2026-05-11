from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Route:
    name: str
    params: dict[str, Any] | None = None


class AppRouter:
    def __init__(self) -> None:
        self.current = Route("home")

    def go(self, name: str, **params: Any) -> Route:
        self.current = Route(name=name, params=params or None)
        return self.current
