"""Tests for the per-user KNX master-data cache and its 7-day refresh."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from editor_gui import master_data
from editor_gui.master_data import _MAX_CACHE_AGE_SECONDS, _load_bytes


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "knx_master.xml"
    monkeypatch.setattr(master_data, "_cache_path", lambda: path)
    return path


def _age(path: Path, seconds: float) -> None:
    stamp = time.time() - seconds
    os.utime(path, (stamp, stamp))


def _returns(value: bytes) -> Callable[..., bytes]:
    def _fetch(**_: object) -> bytes:
        return value

    return _fetch


def test_fresh_cache_is_used_without_fetching(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache.write_bytes(b"OLD")

    def _fail(**_: object) -> bytes:
        raise AssertionError("fresh cache must not fetch")

    monkeypatch.setattr(master_data, "fetch_master_xml", _fail)
    assert _load_bytes() == (b"OLD", "cached")


def test_stale_cache_is_refetched_and_rewritten(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache.write_bytes(b"OLD")
    _age(cache, _MAX_CACHE_AGE_SECONDS + 3600)
    monkeypatch.setattr(master_data, "fetch_master_xml", _returns(b"NEW"))

    assert _load_bytes() == (b"NEW", "fetched")
    assert cache.read_bytes() == b"NEW"


def test_stale_cache_kept_when_refresh_fails(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache.write_bytes(b"OLD")
    _age(cache, _MAX_CACHE_AGE_SECONDS + 3600)

    def _offline(**_: object) -> bytes:
        raise OSError("offline")

    monkeypatch.setattr(master_data, "fetch_master_xml", _offline)
    assert _load_bytes() == (b"OLD", "cached")


def test_missing_cache_fetches_and_caches(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(master_data, "fetch_master_xml", _returns(b"FIRST"))

    assert _load_bytes() == (b"FIRST", "fetched")
    assert cache.read_bytes() == b"FIRST"
