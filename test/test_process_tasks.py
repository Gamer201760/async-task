import asyncio
import logging
from uuid import UUID

import pytest

from domain.task import Task
from test.helpers import run_async
from usecase.interface import DataSource, TaskHandler
from usecase.process import ProcessTasks


def _task(index: int, description: str) -> Task:
    return Task(UUID(int=index + 1), description, priority=index + 1)


class AsyncListSource:
    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = tasks

    def get_tasks(self):
        async def iterator():
            for task in self._tasks:
                yield task

        return iterator()


class RecordingHandler:
    def __init__(self, events: list[tuple[str, str]]) -> None:
        self._events = events

    async def handle(self, task: Task) -> None:
        self._events.append(('start', task.description))
        await asyncio.sleep(0)
        self._events.append(('finish', task.description))


def test_runtime_contract_checks_validate_handler_and_source_inputs() -> None:
    class AsyncHandler:
        async def handle(self, task: Task) -> None:
            return None

    class SyncHandler:
        def handle(self, task: Task) -> None:
            return None

    class InvalidSource:
        pass

    assert isinstance(AsyncListSource([]), DataSource)
    assert not isinstance(InvalidSource(), DataSource)
    assert isinstance(AsyncHandler(), TaskHandler)
    assert not isinstance(object(), TaskHandler)

    with pytest.raises(TypeError, match='TaskHandler'):
        ProcessTasks(SyncHandler())

    process = ProcessTasks(AsyncHandler())

    with pytest.raises(TypeError, match='DataSource'):
        process.add_source(InvalidSource())


def test_execute_awaits_handler_and_preserves_source_order() -> None:
    events: list[tuple[str, str]] = []
    process = ProcessTasks(
        RecordingHandler(events),
        [
            AsyncListSource([_task(0, 'first'), _task(1, 'second')]),
            AsyncListSource([_task(2, 'third')]),
        ],
    )

    run_async(process.execute())

    assert events == [
        ('start', 'first'),
        ('finish', 'first'),
        ('start', 'second'),
        ('finish', 'second'),
        ('start', 'third'),
        ('finish', 'third'),
    ]


def test_execute_logs_handler_failure_and_continues_processing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    attempted: list[str] = []
    handled: list[str] = []

    class SometimesFailingHandler:
        async def handle(self, task: Task) -> None:
            attempted.append(task.description)
            await asyncio.sleep(0)

            if task.description == 'broken':
                raise RuntimeError('boom')

            handled.append(task.description)

    process = ProcessTasks(
        SometimesFailingHandler(),
        [AsyncListSource([_task(0, 'first'), _task(1, 'broken'), _task(2, 'last')])],
    )

    caplog.set_level(logging.INFO, logger='usecase.process')

    run_async(process.execute())

    assert attempted == ['first', 'broken', 'last']
    assert handled == ['first', 'last']
    assert any(
        'Failed to process task' in record.getMessage() for record in caplog.records
    )
    assert any(
        'Processed tasks summary handled=2 failed=1' in record.getMessage()
        for record in caplog.records
    )
