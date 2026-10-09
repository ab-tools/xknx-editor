# JScript oracle

Records the reference results of the script conformance corpus
(`packages/prod/tests/script/conformance/corpus.py`) with the Windows JScript engine
in 32-bit mode, the engine parameter scripts target. The results are committed as
`packages/prod/tests/script/conformance/golden/jscript.json`; the tests compare the
cross-platform runtime against them on every OS.

Windows only, run from the repository root:

```
uv run --with pywin32 --with tzdata python tools/jscript_oracle/record.py --tz Europe/Berlin --locale de-DE
uv run python tools/jscript_oracle/gen_casemap.py
```

`--only <prefix>` re-records a subset of probes. The machine time zone must match `--tz`
and the regional format must match `--locale`.
