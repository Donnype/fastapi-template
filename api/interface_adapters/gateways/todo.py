import os
from collections.abc import Iterator
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session, sessionmaker

from api.domain.entities import Todo, TodoFilter
from api.domain.repositories import TodoRepository
from api.infrastructure.database.client import SQL_BASE, get_engine

class TodoInDB(SQL_BASE):
    __tablename__ = "todo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(length=128), nullable=False, unique=True)
    value = Column(String(length=128), nullable=False)
    done = Column(Boolean, default=False)

class InMemoryTodoRepository(TodoRepository):  # In-memory implementation of interface
    def __init__(self):
        self.data = {}

    def save(self, todo: Todo) -> None:
        self.data[todo.key] = todo

    def get_by_key(self, key: str) -> Todo | None:
        return self.data.get(key)

    def get(self, todo_filter: TodoFilter) -> list[Todo]:
        all_matching_todos = filter(
            lambda todo: (not todo_filter.key_contains or todo_filter.key_contains in todo.key)
            and (not todo_filter.value_contains or todo_filter.value_contains in todo.value)
            and (not todo_filter.done or todo_filter.done == todo.done),
            self.data.values(),
        )

        return list(all_matching_todos)[: todo_filter.limit]


class SQLTodoRepository(TodoRepository):  # SQL Implementation of interface
    def __init__(self, session):
        self._session: Session = session

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:
        if any([exc_type, exc_value, exc_traceback]):
            self._session.rollback()
            return

        try:
            self._session.commit()
        except DatabaseError as e:
            self._session.rollback()
            raise e

    def save(self, todo: Todo) -> None:
        self._session.add(TodoInDB(key=todo.key, value=todo.value))

    def get_by_key(self, key: str) -> Todo | None:
        instance = self._session.query(TodoInDB).filter(TodoInDB.key == key).first()

        if instance:
            return Todo(key=instance.key, value=instance.value, done=instance.done)

        return None

    def get(self, todo_filter: TodoFilter) -> list[Todo]:
        query = self._session.query(TodoInDB)

        if todo_filter.key_contains is not None:
            query = query.filter(TodoInDB.key.contains(todo_filter.key_contains))

        if todo_filter.value_contains is not None:
            query = query.filter(TodoInDB.value.contains(todo_filter.value_contains))

        if todo_filter.done is not None:
            query = query.filter(TodoInDB.done == todo_filter.done)

        if todo_filter.limit is not None:
            query = query.limit(todo_filter.limit)

        return [Todo(key=todo.key, value=todo.value, done=todo.done) for todo in query]

def create_todo_repository() -> Iterator[TodoRepository]:
    session = sessionmaker(bind=get_engine(os.getenv("DB_STRING")))()
    todo_repository = SQLTodoRepository(session)

    try:
        yield todo_repository
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()