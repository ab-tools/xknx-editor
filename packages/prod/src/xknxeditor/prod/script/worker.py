from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any

_STACK_SIZE = 16 * 1024 * 1024


class ScriptWorker:
    """Single thread that runs all script jobs in submission order."""

    def __init__(self, name: str = "script-worker") -> None:
        self._jobs: queue.Queue[tuple[Callable[[], Any], Future[Any]] | None] = (
            queue.Queue()
        )
        previous = threading.stack_size()
        threading.stack_size(_STACK_SIZE)
        try:
            self._thread = threading.Thread(target=self._run, name=name, daemon=True)
            self._thread.start()
        finally:
            threading.stack_size(previous)

    @property
    def thread(self) -> threading.Thread:
        return self._thread

    def submit[T](self, fn: Callable[[], T]) -> Future[T]:
        future: Future[T] = Future()
        if threading.current_thread() is self._thread:
            _run_job(fn, future)
        else:
            self._jobs.put((fn, future))
        return future

    def call[T](self, fn: Callable[[], T]) -> T:
        """Run ``fn`` on the worker and wait for its result."""
        return self.submit(fn).result()

    def shutdown(self) -> None:
        self._jobs.put(None)
        self._thread.join()

    def _run(self) -> None:
        while True:
            item = self._jobs.get()
            if item is None:
                return
            fn, future = item
            _run_job(fn, future)


def _run_job[T](fn: Callable[[], T], future: Future[T]) -> None:
    if not future.set_running_or_notify_cancel():
        return
    try:
        future.set_result(fn())
    except BaseException as exc:
        future.set_exception(exc)


_default: ScriptWorker | None = None
_default_lock = threading.Lock()


def default_worker() -> ScriptWorker:
    global _default
    with _default_lock:
        if _default is None or not _default.thread.is_alive():
            _default = ScriptWorker()
        return _default
