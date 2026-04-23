from dataclasses import dataclass, field
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(slots=True)
class AppResult(Generic[T]):
    success: bool
    data: T | None = None
    errors: list[str] = field(default_factory=list)

    @classmethod
    def ok(cls, data: T | None = None) -> "AppResult[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, *errors: str) -> "AppResult[T]":
        return cls(success=False, errors=list(errors))
