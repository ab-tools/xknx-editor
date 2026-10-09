from __future__ import annotations

import threading

import pytest

from xknxeditor.prod.script import ScriptContext, ScriptWorker


def test_jobs_run_in_order_on_one_thread() -> None:
    worker = ScriptWorker()
    try:
        seen: list[tuple[int, str]] = []
        futures = [
            worker.submit(lambda i=i: seen.append((i, threading.current_thread().name)))
            for i in range(5)
        ]
        for f in futures:
            f.result(timeout=5)
        assert [i for i, _ in seen] == list(range(5))
        assert {name for _, name in seen} == {"script-worker"}
    finally:
        worker.shutdown()


def test_context_on_worker_and_errors() -> None:
    worker = ScriptWorker()
    try:

        def job() -> object:
            ctx = ScriptContext(script="function f(x) { return x + 1; }")
            return ctx.invoke("f", [1]).value

        assert worker.call(job) == 2

        def fail() -> None:
            raise RuntimeError("x")

        with pytest.raises(RuntimeError):
            worker.call(fail)
    finally:
        worker.shutdown()


def test_submit_from_worker_runs_inline() -> None:
    worker = ScriptWorker()
    try:
        assert worker.call(lambda: worker.call(lambda: 5)) == 5
    finally:
        worker.shutdown()
