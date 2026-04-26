from logging import getLogger

from domain.task import Task

logger = getLogger(__name__)


class LoggingTaskHandler:
    async def handle(self, task: Task) -> None:
        logger.info(
            'Handled task id=%s description=%s priority=%s status=%s',
            task.id,
            task.description,
            task.priority,
            task.status.value,
        )
