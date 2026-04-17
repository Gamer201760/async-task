import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

from domain.task import Task
from domain.task_status import TaskStatus


class MockExternalSource:
    def __init__(self) -> None:
        self._payload: list[object] | None = None

    def _task_from_raw(self, item: object) -> Task:
        if not isinstance(item, dict):
            raise TypeError('Каждая запись задачи должна быть словарём')

        missing_fields = [field for field in ('description',) if field not in item]
        if missing_fields:
            raise ValueError(
                'Отсутствуют обязательные поля задачи: ' + ', '.join(missing_fields)
            )

        if 'id' not in item:
            item['id'] = uuid4()

        priority = item.get('priority', 1)
        status = item.get('status', TaskStatus.NEW)

        return Task(
            item['id'],
            item['description'],
            priority,
            status,
        )

    def get_tasks(self) -> AsyncIterator[Task]:
        async def load_payload() -> list[object]:
            if self._payload is None:
                # Кэшируем ответ после первой загрузки, чтобы при повторном вызове
                # не имитировать задержку внешнего источника ещё раз
                await asyncio.sleep(1)
                self._payload = [
                    {
                        'description': 'Check external queue',
                        'priority': 1,
                    },
                    {
                        'id': 'f3a9b7f7-3b23-4f87-aef7-1d22d587d9f1',
                        'description': 'Sync remote task state',
                        'priority': 2,
                        'status': 'in_progress',
                    },
                ]

            return self._payload

        async def iter_tasks() -> AsyncIterator[Task]:
            for item in await load_payload():
                yield self._task_from_raw(item)

        return iter_tasks()
