from collections.abc import AsyncIterator
from inspect import iscoroutinefunction
from logging import getLogger

from domain.task import Task
from usecase.interface import DataSource, TaskHandler

logger = getLogger(__name__)


class ProcessTasks:
    def __init__(
        self,
        handler: TaskHandler,
        sources: list[DataSource] | None = None,
    ) -> None:
        if not isinstance(handler, TaskHandler) or not iscoroutinefunction(
            getattr(handler, 'handle', None)
        ):
            raise TypeError(
                f'Обработчик {handler.__class__.__name__} должен соотвествовать контракту TaskHandler'
            )

        self._handler = handler
        self._sources: list[DataSource] = []

        for source in sources or []:
            self.add_source(source)

    def add_source(self, src: DataSource) -> None:
        if isinstance(src, DataSource):
            self._sources.append(src)
        else:
            raise TypeError(
                f'Источник {src.__class__.__name__} должен соотвествовать контракту DataSource'
            )

    async def _stream_tasks(self) -> AsyncIterator[Task]:
        for source in self._sources:
            source_name = source.__class__.__name__
            logger.info('Start source processing: %s', source_name)
            async for task in source.get_tasks():
                yield task
            logger.info('Finish source processing: %s', source_name)

    async def execute(self) -> None:
        logger.info('Start task processing')

        handled_count = 0
        failed_count = 0
        async for task in self._stream_tasks():
            logger.info('Process task: %s', task)

            try:
                await self._handler.handle(task)
            except Exception:
                failed_count += 1
                logger.exception('Failed to process task: %s', task)
                continue

            handled_count += 1

        logger.info(
            'Processed tasks summary handled=%s failed=%s',
            handled_count,
            failed_count,
        )
