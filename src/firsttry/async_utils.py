import asyncio
import contextlib
from typing import Any


async def _graceful_shutdown(loop: asyncio.AbstractEventLoop) -> None:
    """Cancel and await all remaining tasks, shutdown async generators and default executor."""
    # Avoid cancelling the current shutdown task itself to prevent recursion
    try:
        current = asyncio.current_task(loop)
    except Exception:
        current = None
    tasks = [t for t in asyncio.all_tasks(loop) if t is not current and not t.done()]
    for t in tasks:
        t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.gather(*tasks, return_exceptions=True)
    # shutdown async generators
    try:
        await loop.shutdown_asyncgens()
    except Exception:
        pass
    # shutdown default executor if available
    if hasattr(loop, "shutdown_default_executor"):
        try:
            await loop.shutdown_default_executor()
        except Exception:
            pass


def run_async(coro: Any) -> Any:
    """Run an async coroutine in a fresh event loop and attempt graceful shutdown.

    This is safer than plain asyncio.run when other threads or subprocess
    transports may still be active; it attempts to cancel pending tasks and
    shutdown async generators and executors.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.run_until_complete(_graceful_shutdown(loop))
        except Exception:
            pass
        try:
            loop.close()
        except Exception:
            pass
        # clear global event loop
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass
