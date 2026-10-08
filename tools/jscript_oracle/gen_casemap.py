"""Generate the JScript case mapping table from the recorded conformance results.

uv run python tools/jscript_oracle/gen_casemap.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = (
    ROOT
    / "packages"
    / "prod"
    / "tests"
    / "script"
    / "conformance"
    / "golden"
    / "jscript.json"
)
OUT = (
    ROOT
    / "packages"
    / "prod"
    / "src"
    / "xknxeditor"
    / "prod"
    / "script"
    / "compat"
    / "casemap.json"
)


def main() -> None:
    results = json.loads(GOLDEN.read_text(encoding="utf-8"))["results"]
    upper: dict[str, list[str]] = {}
    lower: dict[str, list[str]] = {}
    for probe_id, value in results.items():
        if not probe_id.startswith("casefull:"):
            continue
        payload = value.split(":", 1)[1]
        if not payload:
            continue
        for entry in payload.split(","):
            code, _, rest = entry.partition(".:.")
            up, _, low = rest.partition("./.")
            up_units = [u for u in up.split(".") if u]
            low_units = [u for u in low.split(".") if u]
            if up_units != [code]:
                upper[code] = up_units
            if low_units != [code]:
                lower[code] = low_units
    OUT.write_text(
        json.dumps({"upper": upper, "lower": lower}, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"upper {len(upper)} lower {len(lower)} -> {OUT}")


if __name__ == "__main__":
    main()
