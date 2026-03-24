from typing import Callable, TypeVar, Awaitable
from knowledge import sandbox_runner

T = TypeVar("T")

async def hem_run_in_sandbox(task: Callable[[], Awaitable[T]]) -> T:
    # Delegate to existing sandbox runner
    return await sandbox_runner.run_in_sandbox(task)
