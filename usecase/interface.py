from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from domain.task import Task


@runtime_checkable
class DataSource(Protocol):
    def get_tasks(self) -> AsyncIterator[Task]: ...


@runtime_checkable
class TaskHandler(Protocol):
    async def handle(self, task: Task) -> None: ...
