"""Source front-end: JScript syntax validation and rewriting for the compatibility runtime."""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any, ClassVar, cast

from ..errors import ScriptCompileError
from ..sandbox import _Interpreter  # pyright: ignore[reportPrivateUsage]

_PKG = "xknxeditor.prod.script.compat"

# JScript compile errors: number = 0x800A0000 | code, as signed 32-bit.
_COMPILE_BASE = -2146828288
_SYNTAX_ERROR = 1002
_COMPILE_CODES = {
    "Syntax error": _SYNTAX_ERROR,
    "Expected ':'": 1003,
    "Expected ';'": 1004,
    "Expected '('": 1005,
    "Expected ')'": 1006,
    "Expected ']'": 1007,
    "Expected '{'": 1008,
    "Expected '}'": 1009,
    "Expected identifier": 1010,
    "Invalid character": 1014,
    "Unterminated string constant": 1015,
    "Unterminated comment": 1016,
}


@cache
def _asset(name: str) -> str:
    return resources.files(_PKG).joinpath(name).read_text(encoding="utf-8")


@dataclass(frozen=True)
class TransformResult:
    code: str
    fnmap: dict[str, str]


_local = threading.local()
_cache: dict[str, TransformResult] = {}
_cache_lock = threading.Lock()


def _interp() -> Any:
    interp: Any = getattr(_local, "interp", None)
    if interp is None:
        interp = _Interpreter()
        interp.evaljs(_asset("acorn.js") + "\n;void 0;")
        interp.evaljs(_asset("frontend.js") + "\n;void 0;")
        _local.interp = interp
    return interp


def _line_col(source: str, pos: int) -> tuple[int, int]:
    line = source.count("\n", 0, pos) + 1
    col = pos - (source.rfind("\n", 0, pos) + 1) + 1
    return line, col


def _compile_error(message: str, source: str, pos: int | None) -> ScriptCompileError:
    text = re.sub(r"\s*\(\d+:\d+\)$", "", message)
    if text not in _COMPILE_CODES:
        text = "Syntax error"
    line, col = _line_col(source, pos or 0)
    return ScriptCompileError(
        text,
        name="SyntaxError",
        number=_COMPILE_BASE + _COMPILE_CODES[text],
        line=line,
        column=col,
    )


def transform(source: str) -> TransformResult:
    """Validate ``source`` as JScript and return the rewritten program."""
    key = hashlib.sha1(source.encode("utf-8", "surrogatepass")).hexdigest()
    with _cache_lock:
        hit = _cache.get(key)
    if hit is not None:
        return hit
    prepared = preprocess_cc(source) if "@" in source else source
    out = cast(
        dict[str, Any], _interp().evaljs("__fe.transform(dukpy.src)", src=prepared)
    )
    if "error" in out:
        err = cast(dict[str, Any], out["error"])
        raise _compile_error(
            str(err.get("message", "")), prepared, cast(int | None, err.get("pos"))
        )
    result = TransformResult(str(out["code"]), cast(dict[str, str], out["fnmap"]))
    with _cache_lock:
        _cache[key] = result
    return result


# Conditional compilation (``@cc_on``) as evaluated by 32-bit JScript.
_CC_VARS: dict[str, float | bool] = {
    "_jscript": True,
    "_jscript_version": 11,
    "_jscript_build": 16384,
    "_win32": True,
    "_x86": True,
    "_microsoft": True,
}
_NAN = float("nan")


class _CcState:
    def __init__(self) -> None:
        self.on = False
        self.vars: dict[str, float | bool] = dict(_CC_VARS)


def preprocess_cc(source: str) -> str:
    """Expand JScript conditional compilation comments once ``@cc_on`` is seen."""
    if "@cc_on" not in source and "@if" not in source and "@set" not in source:
        return source
    state = _CcState()
    out: list[str] = []
    i = 0
    n = len(source)
    last_sig = ""
    while i < n:
        c = source[i]
        if c in "\"'":
            j = _skip_string(source, i)
            out.append(source[i:j])
            last_sig = "a"
            i = j
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            end = n if end < 0 else end + 2
            body = source[i + 2 : end - 2] if end <= n else source[i + 2 :]
            if body.startswith("@") and (state.on or body.startswith("@cc_on")):
                inner = body[1:]
                if inner.endswith("@"):
                    inner = inner[:-1]
                out.append(_cc_code(_cc_directive(inner), state))
            else:
                out.append(source[i:end])
            i = end
            continue
        if source.startswith("//", i):
            m = re.compile(r"[\n\r\u2028\u2029]").search(source, i)
            end = n if m is None else m.start()
            body = source[i + 2 : end]
            if body.startswith("@") and (state.on or body.startswith("@cc_on")):
                out.append(_cc_code(_cc_directive(body[1:]), state))
            else:
                out.append(source[i:end])
            i = end
            continue
        if c == "/" and _regex_allowed(last_sig):
            j = _skip_regex(source, i)
            out.append(source[i:j])
            last_sig = "a"
            i = j
            continue
        if not c.isspace():
            last_sig = c
        out.append(c)
        i += 1
    return "".join(out)


def _cc_directive(content: str) -> str:
    return (
        "@" + content
        if re.match(r"(cc_on|if|elif|else|end|set)(?![A-Za-z0-9_])", content)
        else content
    )


def _skip_string(s: str, i: int) -> int:
    q = s[i]
    j = i + 1
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == q or s[j] in "\n\r":
            return j + 1
        j += 1
    return j


def _regex_allowed(last: str) -> bool:
    return last == "" or last in "(,=:[!&|?{};+-*%<>~^"


def _skip_regex(s: str, i: int) -> int:
    j = i + 1
    in_class = False
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c in "\n\r":
            return j
        if in_class:
            if c == "]":
                in_class = False
        elif c == "[":
            in_class = True
        elif c == "/":
            j += 1
            while j < len(s) and (s[j].isalnum() or s[j] == "_"):
                j += 1
            return j
        j += 1
    return j


_CC_TOKEN = re.compile(
    r"\s*(?:(?P<num>0x[0-9a-fA-F]+|\d+(?:\.\d*)?)|(?P<var>@\w+)|(?P<word>true|false)|"
    r"(?P<op>===|!==|==|!=|<=|>=|&&|\|\||[<>!()+\-*/%&|^~]))"
)


def _cc_code(text: str, state: _CcState) -> str:
    """Expand one conditional compilation block into plain code."""
    state.on = True
    out: list[str] = []
    stack: list[tuple[bool, bool]] = []
    active = True
    pos = 0
    while pos < len(text):
        m = re.compile(r"@(cc_on|if|elif|else|end|set)\b").search(text, pos)
        if m is None:
            if active:
                out.append(_cc_vars(text[pos:], state))
            break
        if active:
            out.append(_cc_vars(text[pos : m.start()], state))
        word = m.group(1)
        pos = m.end()
        if word == "cc_on":
            continue
        if word in ("if", "elif"):
            cond, pos = _cc_paren(text, pos, state)
            if word == "if":
                stack.append((active, False))
                taken = active and _truthy(cond)
                stack[-1] = (active, taken)
                active = taken
            else:
                outer, taken = stack[-1]
                now = outer and not taken and _truthy(cond)
                stack[-1] = (outer, taken or now)
                active = now
        elif word == "else":
            outer, taken = stack[-1] if stack else (True, False)
            active = outer and not taken
            if stack:
                stack[-1] = (outer, True)
        elif word == "end":
            active = stack.pop()[0] if stack else True
        else:
            sm = re.compile(r"\s*@(\w+)\s*=").match(text, pos)
            if sm is None:
                continue
            value, pos = _cc_expr(text, sm.end(), state)
            if active:
                state.vars[sm.group(1)] = value
    return "".join(out)


def _truthy(v: float | bool) -> bool:
    return bool(v) and not (isinstance(v, float) and v != v)


def _cc_value(v: float | bool) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v != v:
        return "NaN"
    return str(int(v)) if float(v).is_integer() else repr(v)


def _cc_vars(text: str, state: _CcState) -> str:
    return re.sub(
        r"@(\w+)", lambda m: _cc_value(state.vars.get(m.group(1), _NAN)), text
    )


def _cc_paren(text: str, pos: int, state: _CcState) -> tuple[float | bool, int]:
    start = text.find("(", pos)
    if start < 0:
        return False, pos
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                value, _ = _cc_expr(text[start + 1 : j], 0, state)
                return value, j + 1
    return False, len(text)


def _cc_expr(text: str, pos: int, state: _CcState) -> tuple[float | bool, int]:
    tokens: list[tuple[str, str]] = []
    while pos < len(text):
        m = _CC_TOKEN.match(text, pos)
        if m is None or m.end() == pos:
            break
        kind = cast(str, m.lastgroup)
        tokens.append((kind, cast(str, m.group(kind))))
        pos = m.end()
        if kind in ("num", "var", "word") and not re.compile(
            r"\s*[<>=!&|+\-*/%^)]"
        ).match(text, pos):
            break
    return _CcParser(tokens, state).parse(), pos


class _CcParser:
    _PREC: ClassVar[dict[str, int]] = {
        "||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "===": 6, "!==": 6,
        "<": 7, ">": 7, "<=": 7, ">=": 7, "+": 8, "-": 8, "*": 9, "/": 9, "%": 9,
    }  # fmt: skip

    def __init__(self, tokens: list[tuple[str, str]], state: _CcState) -> None:
        self.tokens = tokens
        self.i = 0
        self.state = state

    def parse(self) -> float | bool:
        try:
            return self._binary(1)
        except (IndexError, ZeroDivisionError):
            return _NAN

    def _num(self, v: float | bool) -> float:
        return float(v)

    def _unary(self) -> float | bool:
        kind, tok = self.tokens[self.i]
        self.i += 1
        if tok == "!":
            return not _truthy(self._unary())
        if tok == "-":
            return -self._num(self._unary())
        if tok == "+":
            return self._num(self._unary())
        if tok == "(":
            v = self._binary(1)
            self.i += 1
            return v
        if kind == "num":
            return float(int(tok, 16)) if tok.startswith("0x") else float(tok)
        if kind == "word":
            return tok == "true"
        if kind == "var":
            return self.state.vars.get(tok[1:], _NAN)
        return _NAN

    def _binary(self, min_prec: int) -> float | bool:
        left = self._unary()
        while self.i < len(self.tokens):
            op = self.tokens[self.i][1]
            prec = self._PREC.get(op)
            if prec is None or prec < min_prec:
                break
            self.i += 1
            right = self._binary(prec + 1)
            left = _cc_apply(op, left, right)
        return left


def _cc_apply(op: str, a: float | bool, b: float | bool) -> float | bool:
    if op == "||":
        return a if _truthy(a) else b
    if op == "&&":
        return b if _truthy(a) else a
    x, y = float(a), float(b)
    if op in ("==", "==="):
        return x == y
    if op in ("!=", "!=="):
        return x != y
    if op == "<":
        return x < y
    if op == ">":
        return x > y
    if op == "<=":
        return x <= y
    if op == ">=":
        return x >= y
    if op == "+":
        return x + y
    if op == "-":
        return x - y
    if op == "*":
        return x * y
    if op == "/":
        return x / y
    if op == "%":
        return x % y
    ix, iy = int(x), int(y)
    if op == "&":
        return float(ix & iy)
    if op == "|":
        return float(ix | iy)
    return float(ix ^ iy)
