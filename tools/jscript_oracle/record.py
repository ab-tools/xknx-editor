"""Record JScript reference results for the script conformance corpus.

Windows only. Runs every probe in a fresh Active Scripting "JScript" engine (the
engine parameter scripts target) and writes the golden file consumed by the conformance tests.

    uv run --with pywin32 python tools/jscript_oracle/record.py --tz Europe/Berlin --locale de-DE
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import zoneinfo
from pathlib import Path
from typing import Any, ClassVar

import pythoncom  # pyright: ignore
import winerror  # pyright: ignore
from win32com.axscript import axscript  # pyright: ignore
from win32com.server import util  # pyright: ignore
from win32com.server.exception import COMException  # pyright: ignore

ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE = ROOT / "packages" / "prod" / "tests" / "script" / "conformance"


def _load_corpus() -> Any:
    spec = importlib.util.spec_from_file_location("corpus", CONFORMANCE / "corpus.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["corpus"] = module
    spec.loader.exec_module(module)
    return module


class _Site:
    _public_methods_: ClassVar[list[str]] = [
        "GetLCID",
        "GetItemInfo",
        "GetDocVersionString",
        "OnScriptTerminate",
        "OnStateChange",
        "OnScriptError",
        "OnEnterScript",
        "OnLeaveScript",
    ]
    _com_interfaces_: ClassVar[list[Any]] = [axscript.IID_IActiveScriptSite]

    def __init__(self) -> None:
        self.error: str | None = None

    def GetLCID(self) -> int:
        return 0

    def GetItemInfo(self, name: str, mask: int) -> Any:
        raise COMException(scode=winerror.TYPE_E_ELEMENTNOTFOUND)

    def GetDocVersionString(self) -> str:
        return "jscript-oracle"

    def OnScriptTerminate(self, result: Any, excep_info: Any) -> None:
        pass

    def OnStateChange(self, state: int) -> None:
        pass

    def OnScriptError(self, error: Any) -> int:
        info = error.GetExceptionInfo()
        self.error = str(info[2])
        return winerror.S_FALSE

    def OnEnterScript(self) -> None:
        pass

    def OnLeaveScript(self) -> None:
        pass


def _engine() -> tuple[Any, Any, _Site]:
    site = _Site()
    unk = pythoncom.CoCreateInstance(
        "JScript", None, pythoncom.CLSCTX_SERVER, pythoncom.IID_IUnknown
    )
    script = unk.QueryInterface(axscript.IID_IActiveScript)
    parse = unk.QueryInterface(axscript.IID_IActiveScriptParse)
    script.SetScriptSite(util.wrap(site))
    parse.InitNew()
    return script, parse, site


def run_probe(kind: str, program: str) -> str:
    script, parse, site = _engine()
    try:
        try:
            parse.ParseScriptText(program, None, None, None, 0, 0, 0)
        except pythoncom.com_error:
            return "compile-error:" + (site.error or "")
        if site.error is not None:
            return "compile-error:" + site.error
        if kind == "compile":
            return "compile-ok"
        script.SetScriptState(axscript.SCRIPTSTATE_STARTED)
        disp = script.GetScriptDispatch(None)
        try:
            dispid = disp.GetIDsOfNames("__result")
        except pythoncom.com_error:
            return "no-result:" + (site.error or "")
        try:
            return str(disp.Invoke(dispid, 0, pythoncom.DISPATCH_METHOD, True))
        except pythoncom.com_error as exc:
            return "host-error:" + str(exc)
    finally:
        script.Close()


CSCRIPT32 = Path(os.environ.get("WINDIR", r"C:\Windows")) / "SysWOW64" / "cscript.exe"


def run_probe_cscript(kind: str, program: str, workdir: Path) -> str:
    """Run one probe in 32-bit JScript, the bitness parameter scripts run with."""
    script = workdir / "probe.js"
    result = workdir / "result.txt"
    result.unlink(missing_ok=True)
    tail = ""
    if kind != "compile":
        path = json.dumps(str(result))
        tail = (
            "\nvar __fso = new ActiveXObject('Scripting.FileSystemObject');"
            f"var __out = __fso.CreateTextFile({path}, true, true);__out.Write(__result());__out.Close();\n"
        )
    script.write_text(program + tail, encoding="utf-16")
    proc = subprocess.run(
        [str(CSCRIPT32), "//nologo", "//E:jscript", str(script)],
        capture_output=True,
        timeout=60,
        check=False,
    )
    out = result.read_text(encoding="utf-16") if result.exists() else ""
    err = proc.stderr.decode("mbcs", errors="replace")
    if "compilation error" in err.lower():
        match = re.search(r"compilation error:\s*(.*)", err, re.IGNORECASE)
        return "compile-error:" + (match.group(1).strip() if match else "")
    if kind == "compile":
        return "compile-ok"
    if proc.returncode != 0 and not out:
        return (
            "host-error:" + err.strip().splitlines()[-1]
            if err.strip()
            else "host-error"
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tz", default="Europe/Berlin")
    parser.add_argument("--locale", default="de-DE")
    parser.add_argument("--only", default=None, help="probe id prefix")
    parser.add_argument(
        "--axscript", action="store_true", help="use 64-bit Active Scripting in-process"
    )
    args = parser.parse_args()

    zone = zoneinfo.ZoneInfo(args.tz)
    for probe_ts in (1767312000, 1783036800):
        local = datetime.datetime.fromtimestamp(probe_ts).astimezone()
        if (
            local.utcoffset()
            != datetime.datetime.fromtimestamp(probe_ts, zone).utcoffset()
        ):
            raise SystemExit(f"machine time zone does not match {args.tz}")

    corpus = _load_corpus()
    pythoncom.CoInitialize()
    results: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for probe in corpus.probes():
            if args.only and not probe.id.startswith(args.only):
                continue
            program = probe.code if probe.kind == "compile" else corpus.wrap(probe)
            if args.axscript:
                results[probe.id] = run_probe(probe.kind, program)
            else:
                results[probe.id] = run_probe_cscript(probe.kind, program, Path(tmp))

    out = CONFORMANCE / "golden" / "jscript.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if args.only and out.exists():
        existing = json.loads(out.read_text(encoding="utf-8"))["results"]
    existing.update(results)
    version_probe = corpus.Probe(
        "v",
        "expr",
        "ScriptEngine() + ' ' + ScriptEngineMajorVersion() + '.' + ScriptEngineMinorVersion() + '.' + ScriptEngineBuildVersion()",
    )
    with tempfile.TemporaryDirectory() as tmp:
        engine = (
            run_probe("expr", corpus.wrap(version_probe))
            if args.axscript
            else run_probe_cscript("expr", corpus.wrap(version_probe), Path(tmp))
            + " (32-bit)"
        )
    payload = {
        "engine": engine,
        "tz": args.tz,
        "locale": args.locale,
        "results": dict(sorted(existing.items())),
    }
    out.write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(results)} probes recorded -> {out}")


if __name__ == "__main__":
    main()
