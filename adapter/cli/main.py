import argparse
import asyncio
from logging import INFO, basicConfig, getLogger
from random import Random

from adapter.cli.handler import LoggingTaskHandler
from repository.api.mock import MockExternalSource
from repository.file.json import TaskJsonSource
from repository.generator.rand import RandomJobsSource
from usecase.interface import DataSource
from usecase.process import ProcessTasks

basicConfig(format='[%(levelname)s] %(name)s %(asctime)s %(message)s', level=INFO)
logger = getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--file', default='./tasks.jsonl', help='Путь до JSONL-файла с задачами'
    )
    parser.add_argument(
        '--seed', type=int, default=1, help='Seed для генератора случайных задач'
    )
    return parser


async def run(file_path: str, seed: int) -> None:
    handler = LoggingTaskHandler()
    sources: list[DataSource] = [
        MockExternalSource(),
        TaskJsonSource(file_path),
        RandomJobsSource(Random(seed)),
    ]

    logger.info('Waiting data...')
    process = ProcessTasks(handler, sources)
    await process.execute()


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run(args.file, args.seed))


if __name__ == '__main__':
    main()
