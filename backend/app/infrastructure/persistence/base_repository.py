from typing import Generic, TypeVar

from sqlalchemy.orm import Session


TEntity = TypeVar("TEntity")


class BaseRepository(Generic[TEntity]):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: TEntity) -> TEntity:
        self.session.add(entity)
        return entity

    def remove(self, entity: TEntity) -> None:
        self.session.delete(entity)

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
