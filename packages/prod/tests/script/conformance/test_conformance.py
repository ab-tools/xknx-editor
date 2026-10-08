"""The compatibility runtime must reproduce the recorded JScript results exactly."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from xknxeditor.prod.script import ScriptCompileError, ScriptContext, ScriptError
from xknxeditor.prod.script.compat.runtime import JScriptEnv

from .corpus import Probe, probes, wrap

GOLDEN = Path(__file__).parent / "golden" / "jscript.json"

# Behaviour of the JScript engine that is not reproduced; each entry is a known difference.
KNOWN_DIFFERENCES = {
    "err:assign to call": "JScript compiles assignments to call results and fails at run time",
    "compile:in operator for-in var init": "JScript accepts an initializer in a for-in variable declaration",
    "str:regex backref": "JScript fails back-references to groups that did not participate",
    "str:regex brackets": "JScript lexes ']' directly after '[' in a regular expression as a literal",
    "misc:getVarDate": "typeof of a VT_DATE value is 'date' in JScript",
    "mathgen:16": "last-bit difference of the 32-bit JScript math library",
    "mathgen:18": "last-bit difference of the 32-bit JScript math library",
    "mathgen:33": "last-bit difference of the 32-bit JScript math library",
    "mathgen:43": "last-bit difference of the 32-bit JScript math library",
    "mathgen:50": "last-bit difference of the 32-bit JScript math library",
    "mathgen:126": "last-bit difference of the 32-bit JScript math library",
    "mathgen:144": "last-bit difference of the 32-bit JScript math library",
}


@cache
def _golden() -> dict[str, Any]:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@cache
def _env() -> JScriptEnv:
    g = _golden()
    return JScriptEnv(tz=g["tz"], locale=g["locale"])


def _run(probe: Probe) -> str:
    if probe.kind == "compile":
        try:
            ScriptContext(script=probe.code, jscript=_env())
        except ScriptCompileError as exc:
            return "compile-error:" + exc.message
        except ScriptError:
            pass
        return "compile-ok"
    try:
        ctx = ScriptContext(script=wrap(probe), jscript=_env())
    except ScriptCompileError as exc:
        return "compile-error:" + exc.message
    return str(ctx.invoke("__result", []).value)


def _params() -> list[Any]:
    out: list[Any] = []
    for probe in probes():
        marks = []
        if probe.id in KNOWN_DIFFERENCES:
            marks.append(
                pytest.mark.xfail(reason=KNOWN_DIFFERENCES[probe.id], strict=True)
            )
        out.append(pytest.param(probe, id=probe.id, marks=marks))
    return out


@pytest.mark.parametrize("probe", _params())
def test_probe(probe: Probe) -> None:
    expected = _golden()["results"][probe.id]
    actual = _run(probe)
    if probe.kind == "compile":
        assert (actual == "compile-ok") == (expected == "compile-ok"), (
            expected,
            actual,
        )
    else:
        assert actual == expected


def test_golden_covers_corpus() -> None:
    ids = {p.id for p in probes()}
    assert ids == set(_golden()["results"])
