"""Packaging guard: the PyInstaller spec must bundle the data files that our
runtime dependencies load lazily. These are invisible to PyInstaller's import
analysis, so they only reach the frozen app via an explicit collect_all; a
missing one surfaces as a runtime "file is missing" crash on a specific code
path (e.g. dukpy's jsruntime/process_runtime.js when a knxprod runs a parameter
calculation). The static check runs without PyInstaller; the dynamic one
verifies the actual collection when PyInstaller is available."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SPEC = Path(__file__).resolve().parent.parent / "xknx-editor.spec"

# Package -> a data file it loads at runtime that only collect_all bundles.
# Extend this when adding a dependency that ships data loaded lazily at runtime.
REQUIRED_RUNTIME_DATA = {
    "dukpy": "jsruntime/process_runtime.js",
}


def _spec_collect_all_packages() -> set[str]:
    """The string literals passed to collect_all() in the spec's loop."""
    tree = ast.parse(_SPEC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Tuple):
            continue
        calls_collect_all = any(
            isinstance(c, ast.Call)
            and isinstance(c.func, ast.Name)
            and c.func.id == "collect_all"
            for c in ast.walk(node)
        )
        if calls_collect_all:
            return {
                e.value
                for e in node.iter.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            }
    raise AssertionError("no collect_all loop found in xknx-editor.spec")


def test_spec_collects_runtime_data_packages() -> None:
    missing = set(REQUIRED_RUNTIME_DATA) - _spec_collect_all_packages()
    assert not missing, (
        f"packages dropped from the spec's collect_all: {sorted(missing)} "
        "- their runtime data files would be missing from the frozen app"
    )


@pytest.mark.parametrize(("package", "sentinel"), REQUIRED_RUNTIME_DATA.items())
def test_collect_all_bundles_runtime_sentinel(package: str, sentinel: str) -> None:
    hooks = pytest.importorskip("PyInstaller.utils.hooks")
    datas, _binaries, _hidden = hooks.collect_all(package)
    sources = [src.replace("\\", "/") for src, _dst in datas]
    assert any(s.endswith(sentinel) for s in sources), (
        f"collect_all({package!r}) did not bundle {sentinel!r}; sources: {sources[:5]}"
    )
