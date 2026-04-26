import asyncio
from collections.abc import AsyncIterator, Awaitable
from typing import TypeVar

T = TypeVar('T')


async def collect_async(iterator: AsyncIterator[T]) -> list[T]:
    return [item async for item in iterator]


def run_async(awaitable: Awaitable[T]) -> T:
    return asyncio.run(awaitable)
