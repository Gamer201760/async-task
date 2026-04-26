# Лабораторная работа №4 — Асинхронный исполнитель задач

## Цель
Реализовать асинхронную систему обработки задач с расширяемыми источниками и обработчиком через `Protocol`

## Доменная модель
- основная модель задачи находится в [`domain/task.py`](domain/task.py)
- статусы перечислены в [`domain/task_status.py`](domain/task_status.py)
- дескрипторы и доменные ошибки находятся в `domain/`
- `TaskQueue` из 3 лабы сохранён в проекте как отдельная коллекция, но в сценарии 4 лабы не используется как исполнитель

## Контракты
- [`usecase/interface.py`](usecase/interface.py)
- `DataSource` -> `get_tasks() -> AsyncIterator[Task]`
- `TaskHandler` -> `async handle(task: Task) -> None`
  - обработчик отвечает за обработку одной задачи и не управляет обходом источников

## Источники задач
- [`repository/file/json.py`](repository/file/json.py)
  - `TaskJsonSource` читает JSONL асинхронно через `aiofiles`
  - при каждом новом обходе заново открывает файл
  - проверяет обязательные поля и создаёт `Task` лениво
- [`repository/api/mock.py`](repository/api/mock.py)
  - `MockExternalSource` имитирует внешний источник через `await asyncio.sleep(...)`
  - кэширует payload после первой загрузки
- [`repository/generator/rand.py`](repository/generator/rand.py)
  - `RandomJobsSource` генерирует повторяемый набор задач по `seed`
  - переиспользует кэш между повторными обходами одного source

Пример `tasks.jsonl`:

```json
{"id":"12345678-1234-5678-1234-567812345678", "description":"Проверить входные данные JSONL-источника", "priority":2, "status":"new"}
{"id":"87654321-4321-8765-4321-876543218765", "description":"Обновить статус задачи после обработки", "priority":3, "status":"in_progress"}
{"description":"Сформировать итоговый отчёт"}
```

## Оркестрация обработки
- [`usecase/process.py`](usecase/process.py)
  - `ProcessTasks` остаётся оркестратором
  - последовательно обходит зарегистрированные source через `async for`
  - централизованно логирует старт, обработку и итоговую сводку
  - если обработка одной задачи падает, логирует ошибку и продолжает работу с остальными задачами

## Handler
- [`adapter/cli/handler.py`](adapter/cli/handler.py)
  - `LoggingTaskHandler` реализует контракт `TaskHandler`
  - логирует поля обработанной задачи

## CLI
- [`adapter/cli/main.py`](adapter/cli/main.py)
  - собирает `MockExternalSource`, `TaskJsonSource` и `RandomJobsSource`
  - создаёт `ProcessTasks(handler, sources)`
  - запускает обработку через `asyncio.run(...)`

Аргументы CLI:
- `--file` путь до JSONL файла с задачами
- `--seed` seed для генератора случайных задач

Пример запуска:

```bash
uv run python -m adapter.cli.main --file ./tasks.jsonl --seed 42
```

## Запуск и проверки
Требуется Python 3.13+ и `uv`

### Через `make`

```bash
make install
make run
make run ARGS="--file ./tasks.jsonl --seed 42"
make test
make lint
make typecheck
make pre-commit
```

### Через `uv`

```bash
uv sync
uv run python -m adapter.cli.main
uv run python -m adapter.cli.main --file ./tasks.jsonl --seed 42
uv run pytest -q
uv run ruff check .
uv run mypy .
```
