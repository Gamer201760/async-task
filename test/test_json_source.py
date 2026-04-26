import json
from pathlib import Path
from uuid import UUID

import pytest

from domain.task import Task
from domain.task_status import TaskStatus
from repository.file.json import TaskJsonSource
from test.helpers import collect_async, run_async


def _write_jsonl_file(tmp_path: Path, payload: list[object]) -> Path:
    path = tmp_path / 'tasks.jsonl'
    path.write_text(
        '\n'.join(json.dumps(item) for item in payload) + '\n',
        encoding='utf-8',
    )
    return path


def _collect_tasks(source: TaskJsonSource) -> list[Task]:
    return run_async(collect_async(source.get_tasks()))


def test_get_tasks_returns_task_objects_for_valid_json_with_full_fields(
    tmp_path: Path,
) -> None:
    path = _write_jsonl_file(
        tmp_path,
        [
            {
                'id': '12345678-1234-5678-1234-567812345678',
                'description': 'Write JSON tests',
                'priority': 3,
                'status': 'in_progress',
            },
            {
                'id': '87654321-4321-8765-4321-876543218765',
                'description': 'Review JSON tests',
                'priority': 5,
                'status': 'done',
            },
        ],
    )

    tasks = _collect_tasks(TaskJsonSource(path))

    assert len(tasks) == 2
    assert all(isinstance(task, Task) for task in tasks)
    assert tasks[0].id == UUID('12345678-1234-5678-1234-567812345678')
    assert tasks[0].description == 'Write JSON tests'
    assert tasks[0].priority == 3
    assert tasks[0].status is TaskStatus.IN_PROGRESS
    assert tasks[1].id == UUID('87654321-4321-8765-4321-876543218765')
    assert tasks[1].description == 'Review JSON tests'
    assert tasks[1].priority == 5
    assert tasks[1].status is TaskStatus.DONE


def test_get_tasks_generates_uuid_and_defaults_priority_and_status_when_optional_fields_are_missing(
    tmp_path: Path,
) -> None:
    path = _write_jsonl_file(tmp_path, [{'description': 'Create task from JSON'}])

    tasks = _collect_tasks(TaskJsonSource(path))

    assert len(tasks) == 1
    assert isinstance(tasks[0].id, UUID)
    assert tasks[0].description == 'Create task from JSON'
    assert tasks[0].priority == 1
    assert tasks[0].status is TaskStatus.NEW


def test_get_tasks_reads_jsonl_lazily_when_iteration_starts(tmp_path: Path) -> None:
    path = _write_jsonl_file(tmp_path, [{'description': 'Before iteration'}])
    source = TaskJsonSource(path)
    iterator = source.get_tasks()

    path.write_text(
        json.dumps(
            {
                'description': 'After iteration starts',
                'priority': 2,
                'status': 'done',
            }
        )
        + '\n',
        encoding='utf-8',
    )

    tasks = run_async(collect_async(iterator))

    assert [task.description for task in tasks] == ['After iteration starts']
    assert tasks[0].priority == 2
    assert tasks[0].status is TaskStatus.DONE


def test_get_tasks_raises_file_not_found_error_when_async_iteration_begins(
    tmp_path: Path,
) -> None:
    iterator = TaskJsonSource(tmp_path / 'missing.jsonl').get_tasks()

    with pytest.raises(FileNotFoundError):
        run_async(collect_async(iterator))


def test_get_tasks_raises_is_a_directory_error_for_directory_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(IsADirectoryError):
        _collect_tasks(TaskJsonSource(tmp_path))


def test_get_tasks_raises_value_error_for_invalid_jsonl_line(tmp_path: Path) -> None:
    path = tmp_path / 'invalid.jsonl'
    path.write_text('{"broken": \n', encoding='utf-8')

    with pytest.raises(ValueError, match='строка 1'):
        _collect_tasks(TaskJsonSource(path))


def test_get_tasks_raises_type_error_when_jsonl_line_is_not_a_dict(
    tmp_path: Path,
) -> None:
    path = _write_jsonl_file(tmp_path, ['not-a-task-mapping'])

    with pytest.raises(TypeError):
        _collect_tasks(TaskJsonSource(path))


def test_get_tasks_raises_value_error_when_description_is_missing(
    tmp_path: Path,
) -> None:
    path = _write_jsonl_file(tmp_path, [{'priority': 2, 'status': 'new'}])

    with pytest.raises(ValueError, match='description'):
        _collect_tasks(TaskJsonSource(path))


def test_get_tasks_reopens_jsonl_file_for_each_new_iteration(tmp_path: Path) -> None:
    path = _write_jsonl_file(
        tmp_path,
        [{'description': 'First version', 'priority': 1, 'status': 'new'}],
    )
    source = TaskJsonSource(path)

    first_pass = _collect_tasks(source)

    path.write_text(
        json.dumps(
            {
                'description': 'Second version',
                'priority': 2,
                'status': 'done',
            }
        )
        + '\n',
        encoding='utf-8',
    )

    second_pass = _collect_tasks(source)

    assert [task.description for task in first_pass] == ['First version']
    assert [task.description for task in second_pass] == ['Second version']
    assert second_pass[0].priority == 2
    assert second_pass[0].status is TaskStatus.DONE
