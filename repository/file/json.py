import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import aiofiles

from domain.task import Task
from domain.task_status import TaskStatus


class TaskJsonSource:
    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

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
        async def iter_raw_tasks() -> AsyncIterator[object]:
            if not await asyncio.to_thread(self._path.exists):
                raise FileNotFoundError(f'Файл с задачами не найден: {self._path}')
            if not await asyncio.to_thread(self._path.is_file):
                raise IsADirectoryError(
                    f'Ожидался файл, но получен каталог: {self._path}'
                )

            async with aiofiles.open(self._path, encoding='utf-8') as file:
                line_number = 0
                async for line in file:
                    line_number += 1
                    raw_line = line.strip()
                    if not raw_line:
                        continue

                    try:
                        yield json.loads(raw_line)
                    except json.JSONDecodeError as err:
                        raise ValueError(
                            f'Некорректный JSONL в файле с задачами: {self._path}, строка {line_number}'
                        ) from err

        async def iter_tasks() -> AsyncIterator[Task]:
            async for item in iter_raw_tasks():
                yield self._task_from_raw(item)

        return iter_tasks()
