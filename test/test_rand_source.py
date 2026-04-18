from random import Random
from typing import cast
from uuid import UUID

import pytest

from domain.task import Task
from domain.task_status import TaskStatus
from repository.generator.rand import RandomJobsSource
from test.helpers import collect_async, run_async


def _source_with_raw_tasks(
    monkeypatch: pytest.MonkeyPatch,
    raw_tasks: list[object],
    seed: int = 1,
) -> RandomJobsSource:
    source = RandomJobsSource(Random(seed))
    monkeypatch.setattr(source, '_generate_raw_tasks', lambda: list(raw_tasks))

    return source


def _task_snapshot(task: Task) -> tuple[UUID, str, int, TaskStatus]:
    return (
        task.id,
        cast(str, task.description),
        cast(int, task.priority),
        task.status,
    )


def _collect_tasks(source: RandomJobsSource) -> list[Task]:
    return run_async(collect_async(source.get_tasks()))


def test_get_tasks_returns_non_empty_iterable_of_tasks() -> None:
    tasks = _collect_tasks(RandomJobsSource(Random(1)))

    assert tasks
    assert all(isinstance(task, Task) for task in tasks)


def test_same_seed_yields_reproducible_mapped_tasks() -> None:
    left = _collect_tasks(RandomJobsSource(Random(7)))
    right = _collect_tasks(RandomJobsSource(Random(7)))

    assert [_task_snapshot(task) for task in left] == [
        _task_snapshot(task) for task in right
    ]


def test_generated_tasks_have_uuid_ids_non_empty_descriptions_and_valid_priorities() -> (
    None
):
    tasks = _collect_tasks(RandomJobsSource(Random(11)))

    assert tasks
    for task in tasks:
        assert isinstance(task.id, UUID)
        assert task.description
        assert isinstance(task.priority, int)
        assert task.priority >= 1


def test_same_source_reuses_cached_payload_on_new_iteration() -> None:
    source = RandomJobsSource(Random(7))

    first_pass = _collect_tasks(source)
    second_pass = _collect_tasks(source)

    assert [_task_snapshot(task) for task in first_pass] == [
        _task_snapshot(task) for task in second_pass
    ]


def test_missing_status_defaults_to_task_status_new(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks = _collect_tasks(
        _source_with_raw_tasks(
            monkeypatch,
            [{'description': 'Default status task', 'priority': 2}],
        )
    )

    assert len(tasks) == 1
    assert tasks[0].status is TaskStatus.NEW


def test_explicit_id_and_status_are_preserved_after_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit_id = '87654321-4321-8765-4321-876543218765'

    tasks = _collect_tasks(
        _source_with_raw_tasks(
            monkeypatch,
            [
                {
                    'id': explicit_id,
                    'description': 'Explicit status task',
                    'priority': 3,
                    'status': 'done',
                }
            ],
        )
    )

    assert len(tasks) == 1
    assert tasks[0].id == UUID(explicit_id)
    assert tasks[0].status is TaskStatus.DONE


def test_missing_id_generates_deterministic_uuid_and_defaults_missing_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated_id = UUID('12345678-1234-5678-1234-567812345678')
    source = _source_with_raw_tasks(
        monkeypatch,
        [{'description': 'Generated id task'}],
    )
    monkeypatch.setattr(source, '_generate_task_id', lambda: generated_id)

    tasks = _collect_tasks(source)

    assert len(tasks) == 1
    assert tasks[0].id == generated_id
    assert tasks[0].priority == 1
    assert tasks[0].status is TaskStatus.NEW


def test_invalid_explicit_id_propagates_uuid_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError):
        _collect_tasks(
            _source_with_raw_tasks(
                monkeypatch,
                [
                    {
                        'id': 'not-a-uuid',
                        'description': 'Bad id task',
                        'priority': 2,
                    }
                ],
            )
        )


def test_non_dict_raw_items_raise_type_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(TypeError):
        _collect_tasks(
            _source_with_raw_tasks(
                monkeypatch,
                ['not-a-task-mapping'],
            )
        )


def test_missing_description_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match='description'):
        _collect_tasks(
            _source_with_raw_tasks(
                monkeypatch,
                [{'priority': 4, 'status': 'new'}],
            )
        )


def test_missing_priority_defaults_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    tasks = _collect_tasks(
        _source_with_raw_tasks(
            monkeypatch,
            [{'description': 'Missing priority'}],
        )
    )

    assert len(tasks) == 1
    assert tasks[0].description == 'Missing priority'
    assert tasks[0].priority == 1
    assert tasks[0].status is TaskStatus.NEW
