"""Probe corpus for JScript conformance; consumed by the oracle recorder and the tests.

Probe kinds:
- ``expr``: a JS expression.
- ``body``: function body statements; the probe value is its return value.
- ``program``: program text that defines ``function probe()``.
- ``compile``: program text; only acceptance by the parser is compared.
"""

from __future__ import annotations

import random
from typing import NamedTuple


class Probe(NamedTuple):
    id: str
    kind: str
    code: str


HARNESS = r"""
function __show(v) {
  if (v === null) return "null";
  var t = typeof v;
  var s;
  try { s = String(v); } catch (e) { s = "<" + e.message + ">"; }
  return t + ":" + s;
}
function __run(f) {
  try { return __show(f()); }
  catch (e) {
    if (e === null || typeof e !== "object") return "throws-value:" + __show(e);
    return "throws:" + e.name + "|" + e.message + "|" + e.number + "|" + e.description;
  }
}
"""


def wrap(probe: Probe) -> str:
    """Program text that defines ``__result()`` for a non-compile probe."""
    if probe.kind == "expr":
        return (
            HARNESS
            + "function __result() { return __run(function () { return ("
            + probe.code
            + "\n); }); }\n"
        )
    if probe.kind == "body":
        return (
            HARNESS
            + "function __result() { return __run(function () {\n"
            + probe.code
            + "\n}); }\n"
        )
    if probe.kind == "program":
        return HARNESS + probe.code + "\nfunction __result() { return __run(probe); }\n"
    raise ValueError(probe.kind)


_QUICKJS_OWN = {
    "": "AggregateError Array ArrayBuffer Atomics BigInt BigInt64Array BigUint64Array Boolean DOMException DataView Date Error EvalError FinalizationRegistry Float16Array Float32Array Float64Array Function Infinity Int16Array Int32Array Int8Array InternalError Iterator JSON Map Math NaN Number Object Promise Proxy RangeError ReferenceError Reflect RegExp Set SharedArrayBuffer String Symbol SyntaxError TypeError URIError Uint16Array Uint32Array Uint8Array Uint8ClampedArray WeakMap WeakRef WeakSet decodeURI decodeURIComponent encodeURI encodeURIComponent escape eval globalThis isFinite isNaN parseFloat parseInt performance queueMicrotask undefined unescape ActiveXObject Enumerator VBArray GetObject ScriptEngine ScriptEngineMajorVersion ScriptEngineMinorVersion ScriptEngineBuildVersion CollectGarbage Debug console window print setTimeout",
    "Object": "assign create defineProperties defineProperty entries freeze fromEntries getOwnPropertyDescriptor getOwnPropertyDescriptors getOwnPropertyNames getOwnPropertySymbols getPrototypeOf groupBy hasOwn is isExtensible isFrozen isSealed keys length name preventExtensions prototype seal setPrototypeOf values",
    "Object.prototype": "__defineGetter__ __defineSetter__ __lookupGetter__ __lookupSetter__ __proto__ constructor hasOwnProperty isPrototypeOf propertyIsEnumerable toLocaleString toString valueOf",
    "Function.prototype": "apply arguments bind call caller columnNumber constructor fileName length lineNumber name toString",
    "Array": "from fromAsync isArray length name of prototype",
    "Array.prototype": "at concat constructor copyWithin entries every fill filter find findIndex findLast findLastIndex flat flatMap forEach includes indexOf join keys lastIndexOf length map pop push reduce reduceRight reverse shift slice some sort splice toLocaleString toReversed toSorted toSpliced toString unshift values with",
    "String": "fromCharCode fromCodePoint length name prototype raw",
    "String.prototype": "anchor at big blink bold charAt charCodeAt codePointAt concat constructor endsWith fixed fontcolor fontsize includes indexOf isWellFormed italics lastIndexOf length link localeCompare match matchAll normalize padEnd padStart repeat replace replaceAll search slice small split startsWith strike sub substr substring sup toLocaleLowerCase toLocaleUpperCase toLowerCase toString toUpperCase toWellFormed trim trimEnd trimLeft trimRight trimStart valueOf",
    "Number": "EPSILON MAX_SAFE_INTEGER MAX_VALUE MIN_SAFE_INTEGER MIN_VALUE NEGATIVE_INFINITY NaN POSITIVE_INFINITY isFinite isInteger isNaN isSafeInteger length name parseFloat parseInt prototype",
    "Number.prototype": "constructor toExponential toFixed toLocaleString toPrecision toString valueOf",
    "Boolean.prototype": "constructor toString valueOf",
    "Math": "E LN10 LN2 LOG10E LOG2E PI SQRT1_2 SQRT2 abs acos acosh asin asinh atan atan2 atanh cbrt ceil clz32 cos cosh exp expm1 f16round floor fround hypot imul log log10 log1p log2 max min pow random round sign sin sinh sqrt sumPrecise tan tanh trunc",
    "Date": "UTC length name now parse prototype",
    "Date.prototype": "constructor getDate getDay getFullYear getHours getMilliseconds getMinutes getMonth getSeconds getTime getTimezoneOffset getUTCDate getUTCDay getUTCFullYear getUTCHours getUTCMilliseconds getUTCMinutes getUTCMonth getUTCSeconds getYear setDate setFullYear setHours setMilliseconds setMinutes setMonth setSeconds setTime setUTCDate setUTCFullYear setUTCHours setUTCMilliseconds setUTCMinutes setUTCMonth setUTCSeconds setYear toDateString toGMTString toISOString toJSON toLocaleDateString toLocaleString toLocaleTimeString toString toTimeString toUTCString valueOf getVarDate",
    "RegExp": "escape length name prototype $1 $2 $9 input lastMatch lastParen leftContext rightContext index lastIndex $_",
    "RegExp.prototype": "compile constructor dotAll exec flags global hasIndices ignoreCase multiline source sticky test toString unicode unicodeSets lastIndex",
    "Error": "captureStackTrace isError length name prepareStackTrace prototype stackTraceLimit",
    "Error.prototype": "constructor message name toString description number stack",
}


def _presence() -> list[Probe]:
    probes: list[Probe] = []
    for owner, names in _QUICKJS_OWN.items():
        for name in names.split():
            if not owner:
                probes.append(Probe(f"has:{name}", "expr", f"typeof {name}"))
            else:
                probes.append(
                    Probe(
                        f"has:{owner}.{name}",
                        "expr",
                        f"('{name}' in {owner}) + '/' + typeof {owner}['{name}']",
                    )
                )
    probes.append(Probe("has:new Error().stack", "expr", "typeof new Error('x').stack"))
    probes.append(
        Probe(
            "has:error own keys",
            "body",
            "var e = new Error('x'); var k = []; for (var p in e) k.push(p); return k.join(',');",
        )
    )
    probes.append(
        Probe(
            "has:engine version",
            "expr",
            "ScriptEngine() + ' ' + ScriptEngineMajorVersion() + '.' + ScriptEngineMinorVersion() + '.' + ScriptEngineBuildVersion()",
        )
    )
    return probes


_SEMANTIC: list[tuple[str, str, str]] = [
    # errors
    ("err:toString", "expr", "String(new Error('m'))"),
    ("err:typeerror toString", "expr", "String(new TypeError('m'))"),
    (
        "err:props",
        "body",
        "var e = new Error('m'); return [e.message, e.description, e.number, e.name].join('|');",
    ),
    (
        "err:number ctor",
        "body",
        "var e = new Error(5, 'desc'); return [e.message, e.description, e.number, e.name].join('|');",
    ),
    (
        "err:number ctor neg",
        "body",
        "var e = new Error(-2146827850, 'x'); return [e.message, e.description, e.number].join('|');",
    ),
    (
        "err:no args",
        "body",
        "var e = new Error(); return [e.message, e.description, e.number].join('|');",
    ),
    (
        "err:Error()",
        "body",
        "var e = Error('f'); return [e.message, e instanceof Error].join('|');",
    ),
    (
        "err:set message",
        "body",
        "var e = new Error('a'); e.message = 'b'; return [e.message, e.description].join('|');",
    ),
    (
        "err:set description",
        "body",
        "var e = new Error('a'); e.description = 'c'; return [e.message, e.description].join('|');",
    ),
    ("err:call undefined method", "body", "var o = {}; o.nope();"),
    ("err:call non-function member", "body", "var o = {x: 1}; o.x();"),
    ("err:call null member", "body", "var o = {x: null}; o.x();"),
    ("err:call computed member", "body", "var o = {}; o['no' + 'pe']();"),
    ("err:call undefined var", "body", "undefinedFn123();"),
    ("err:call non-function var", "body", "var x = 1; x();"),
    ("err:read undefined var", "body", "return undefinedVar123 + 1;"),
    ("err:typeof undefined var", "expr", "typeof undefinedVar123"),
    ("err:prop of null", "body", "var o = null; return o.x;"),
    ("err:prop of undefined", "body", "var o; return o.x;"),
    ("err:set prop of null", "body", "var o = null; o.x = 1;"),
    ("err:method of null", "body", "var o = null; o.m();"),
    ("err:nested prop", "body", "var o = {}; return o.a.b;"),
    ("err:computed prop of null", "body", "var o = null; return o['k'];"),
    ("err:new non-constructor", "body", "var x = 1; new x();"),
    ("err:new undefined", "body", "new UndefinedCtor123();"),
    ("err:new object", "body", "var o = {}; new o();"),
    ("err:instanceof", "body", "return {} instanceof 3;"),
    ("err:in", "body", "return 'a' in 3;"),
    ("err:array length", "body", "return new Array(-1);"),
    ("err:toFixed range", "body", "return (1).toFixed(30);"),
    ("err:toPrecision range", "body", "return (1).toPrecision(0);"),
    ("err:toString radix", "body", "return (1).toString(1);"),
    ("err:stack overflow", "body", "function r() { return r() + 1; } return r();"),
    ("err:throw string", "body", "throw 'x';"),
    ("err:throw number", "body", "throw 42;"),
    ("err:throw object", "body", "throw {message: 'm', name: 'N'};"),
    (
        "err:catch name",
        "body",
        "try { null.x; } catch (e) { return [e.name, e instanceof TypeError, e instanceof Error, typeof e.number].join('|'); }",
    ),
    (
        "err:catch reference",
        "body",
        "try { noSuchVar999; } catch (e) { return [e.name, e instanceof ReferenceError, e instanceof TypeError].join('|'); }",
    ),
    (
        "err:string of caught",
        "body",
        "try { var o = {}; o.f(); } catch (e) { return '' + e + '|' + e.toString(); }",
    ),
    (
        "err:syntax via eval",
        "body",
        "try { eval('var ='); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:uri",
        "body",
        "try { decodeURIComponent('%'); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:regexp syntax",
        "body",
        "try { new RegExp('('); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:Function ctor syntax",
        "body",
        "try { new Function('{'); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    ("err:date invalid toString", "expr", "String(new Date(NaN))"),
    (
        "err:valueOf throws",
        "body",
        "var o = {valueOf: function () { throw new Error('v'); }}; return o + 1;",
    ),
    (
        "err:object to primitive",
        "body",
        "var o = {valueOf: function () { return {}; }, toString: function () { return {}; }}; return o + 1;",
    ),
    (
        "err:call apply non-array",
        "body",
        "function f() { return arguments.length; } return f.apply(null, 5);",
    ),
    (
        "err:call apply array-like",
        "body",
        "function f() { return arguments.length; } return f.apply(null, {length: 2});",
    ),
    ("err:delete var", "body", "var x = 1; return delete x;"),
    ("err:assign to call", "compile", "f() = 1;"),
    # numbers
    (
        "num:parseInt octal",
        "expr",
        "[parseInt('08'), parseInt('010'), parseInt('0x1F'), parseInt(' 12px'), parseInt('-08'), parseInt('0'), parseInt('09', 10), parseInt('')].join(',')",
    ),
    (
        "num:parseInt whitespace",
        "expr",
        "[parseInt('\\u00a012'), parseInt('\\u200012'), parseInt('\\ufeff12'), parseInt('\\t\\n\\v\\f\\r 12')].join(',')",
    ),
    (
        "num:parseFloat",
        "expr",
        "[parseFloat('1e3x'), parseFloat('.5'), parseFloat('-.5e-1'), parseFloat('Infinityx'), parseFloat('\\u00a01.5'), parseFloat('0x10')].join(',')",
    ),
    (
        "num:Number()",
        "expr",
        "[Number(''), Number(' 12 '), Number('1e3'), Number('.5'), Number('0x1f'), Number('1,5'), Number('\\u00a05'), Number('08'), Number('-0x10'), Number('Infinity'), Number(null), Number(undefined), Number([]), Number([7]), Number(true)].join(',')",
    ),
    (
        "num:toString",
        "expr",
        "[1e21, 1e-7, 123456789012345680000, 0.1 + 0.2, -0, 1 / 3, 100, 1e100, 5e-324, 1.7976931348623157e308, 0.000001, 1e-6, 123e-20, 2e20].join(',')",
    ),
    (
        "num:toString radix",
        "expr",
        "[(255).toString(16), (-255).toString(2), (0.5).toString(2), (3.75).toString(16), (1e21).toString(36), (0.1).toString(3), (-0).toString(2)].join(',')",
    ),
    (
        "num:toFixed",
        "expr",
        "[(0.5).toFixed(0), (1.5).toFixed(0), (2.5).toFixed(0), (1.005).toFixed(2), (1.45).toFixed(1), (8.345).toFixed(2), (0.000001).toFixed(7), (1e21).toFixed(2), (-1.5).toFixed(0), (-0.5).toFixed(0), (123.456).toFixed(), (0).toFixed(2), (-0).toFixed(2), (1.255).toFixed(2), (10.235).toFixed(2), (1e20).toFixed(2), (0.0005).toFixed(3)].join(',')",
    ),
    (
        "num:toPrecision",
        "expr",
        "[(123.456).toPrecision(4), (0.00001).toPrecision(1), (1.005).toPrecision(3), (123456).toPrecision(2), (1e21).toPrecision(3), (0).toPrecision(3), (-1.45).toPrecision(2), (1).toPrecision()].join(',')",
    ),
    (
        "num:toExponential",
        "expr",
        "[(123.456).toExponential(2), (0).toExponential(1), (1.005).toExponential(2), (1e21).toExponential(), (-1.45).toExponential(1), (5).toExponential()].join(',')",
    ),
    (
        "num:toLocaleString",
        "expr",
        "[(1234.5).toLocaleString(), (0).toLocaleString(), (-1234567.891).toLocaleString(), (1e21).toLocaleString(), (0.125).toLocaleString(), (NaN).toLocaleString()].join(';')",
    ),
    (
        "num:math round",
        "expr",
        "[Math.round(-0.5), Math.round(2.5), Math.round(-2.5), Math.round(0.49999999999999994), Math.round(-1.5)].join(',')",
    ),
    (
        "num:math minmax",
        "expr",
        "[Math.max(), Math.min(), Math.max(1, NaN), Math.min('2', 1), Math.max(-0, 0)].join(',')",
    ),
    (
        "num:math misc",
        "expr",
        "[Math.pow(0, 0), Math.pow(NaN, 0), Math.pow(1, Infinity), Math.atan2(0, -0), Math.sqrt(-1), Math.abs(-0), Math.ceil(-0.5), Math.floor(-0.5)].join(',')",
    ),
    (
        "num:int ops",
        "expr",
        "[(0xFFFFFFFF | 0), (1 << 31), (-1 >>> 0), (5 / 2 | 0), (-7 % 3), (2147483648 >> 0), (1e21 | 0), (-0.5 | 0)].join(',')",
    ),
    (
        "num:isNaN",
        "expr",
        "[isNaN('abc'), isNaN(''), isNaN(' '), isFinite('12'), isFinite(null)].join(',')",
    ),
    ("num:octal literal", "expr", "010 + 0"),
    ("num:octal escape", "expr", "'\\101\\60'"),
    (
        "num:float parse precision",
        "expr",
        "[0.1 * 3, 1.1 + 2.2, 9007199254740993, 1e16 + 1].join(',')",
    ),
    # strings
    (
        "str:substr",
        "expr",
        "['abcdef'.substr(-2, 1), 'abcdef'.substr(2), 'abcdef'.substr(-10), 'abcdef'.substr(1, -1), 'abc'.substr(-1)].join('|')",
    ),
    (
        "str:substring",
        "expr",
        "['abcdef'.substring(4, 1), 'abcdef'.substring(-1, 2), 'abcdef'.substring(NaN, 3)].join('|')",
    ),
    (
        "str:slice",
        "expr",
        "['abcdef'.slice(-2), 'abcdef'.slice(1, -1), 'abcdef'.slice(4, 1)].join('|')",
    ),
    ("str:index", "expr", "typeof 'abc'[1]"),
    ("str:index value", "expr", "'abc'[1]"),
    ("str:index length", "expr", "'abc'['length']"),
    ("str:object index", "expr", "typeof new String('abc')[1]"),
    (
        "str:charAt",
        "expr",
        "['abc'.charAt(5), 'abc'.charAt(-1), 'abc'.charAt(1.7)].join('|')",
    ),
    (
        "str:charCodeAt",
        "expr",
        "['a'.charCodeAt(5), 'a'.charCodeAt(-1), 'a'.charCodeAt()].join('|')",
    ),
    (
        "str:indexOf",
        "expr",
        "['abcabc'.indexOf('c', -5), 'abc'.indexOf(''), 'abc'.indexOf('', 10), 'abcabc'.lastIndexOf('a', -1), 'abcabc'.lastIndexOf('c', 100), 'abc'.lastIndexOf('')].join(',')",
    ),
    ("str:split regex capture", "expr", "'a1b2c'.split(/(\\d)/).join('|')"),
    ("str:split capture length", "expr", "'a1b2c'.split(/(\\d)/).length"),
    (
        "str:split empty regex",
        "expr",
        "'abc'.split(/(?:)/).join('|') + '#' + 'abc'.split(/(?:)/).length",
    ),
    (
        "str:split empty string",
        "expr",
        "'abc'.split('').join('|') + '#' + ''.split('').length + '#' + ''.split(',').length",
    ),
    (
        "str:split limit",
        "expr",
        "['a,b,c'.split(',', 2).join('|'), 'a,b,c'.split(',', 0).length, 'a,b,c'.split(',', -1).length].join('#')",
    ),
    (
        "str:split undefined",
        "expr",
        "'abc'.split(undefined).length + '#' + 'abc'.split().length",
    ),
    (
        "str:split regex edge",
        "expr",
        "['a,,b'.split(/,/).join('|'), ',a,'.split(/,/).length, 'ab'.split(/a*?/).join('|'), 'ab'.split(/a*/).join('|'), 'test'.split(/(?:t)/).length].join('#')",
    ),
    ("str:split regex global", "expr", "'a b  c'.split(/\\s+/g).join('|')"),
    ("str:replace string $", "expr", "'abc'.replace('b', '[$&$$$1]')"),
    ("str:replace regex $", "expr", "'abc'.replace(/(b)/, '[$&|$$|$1|$2|$`|$\\']')"),
    (
        "str:replace fn args",
        "expr",
        "'a1b2'.replace(/(\\d)/g, function (m, p1, off, s) { return '<' + m + p1 + off + typeof s + arguments.length + '>'; })",
    ),
    (
        "str:replace string fn",
        "expr",
        "'abcb'.replace('b', function (m, off, s) { return '<' + m + off + s + arguments.length + '>'; })",
    ),
    (
        "str:replace unmatched group",
        "expr",
        "'b'.replace(/(a)|(b)/, function (m, p1, p2) { return typeof p1 + '|' + p1 + '|' + p2; })",
    ),
    ("str:replace unmatched $", "expr", "'b'.replace(/(a)|(b)/, '[$1][$2]')"),
    (
        "str:replace global lastIndex",
        "body",
        "var r = /a/g; r.lastIndex = 5; var s = 'aaa'.replace(r, 'b'); return s + '|' + r.lastIndex;",
    ),
    ("str:match global", "expr", "'a1b2'.match(/\\d/g).join(',')"),
    ("str:match none", "expr", "'abc'.match(/\\d/g)"),
    ("str:match string arg", "expr", "'a.c'.match('.').index"),
    (
        "str:search",
        "expr",
        "['abc'.search('c'), 'abc'.search(/x/), 'a.c'.search('.')].join(',')",
    ),
    ("str:concat", "expr", "'a'.concat(1, null, undefined, [2, 3])"),
    (
        "str:case",
        "expr",
        "'aBc\\u00e4\\u00df\\u0131\\u0130'.toUpperCase() + '|' + 'AbC\\u00c4\\u0130'.toLowerCase()",
    ),
    (
        "str:case length",
        "expr",
        "'\\u00df'.toUpperCase().length + ',' + '\\u0130'.toLowerCase().length + ',' + '\\ufb00'.toUpperCase().length",
    ),
    (
        "str:localeCompare",
        "expr",
        "['a'.localeCompare('B'), 'B'.localeCompare('a'), 'a'.localeCompare('A'), '\\u00e4'.localeCompare('b'), 'z'.localeCompare('\\u00e4'), 'a'.localeCompare('a'), 'ab'.localeCompare('a'), '10'.localeCompare('9')].join(',')",
    ),
    ("str:locale case", "expr", "'i'.toLocaleUpperCase() + 'I'.toLocaleLowerCase()"),
    (
        "str:html",
        "expr",
        "'x'.anchor('a\"b') + 'x'.bold() + 'x'.link('u') + 'x'.fontcolor('red')",
    ),
    (
        "str:fromCharCode",
        "expr",
        "String.fromCharCode(72, 105, 65536 + 65) + '|' + String.fromCharCode().length",
    ),
    ("str:escape", "expr", "escape(String.fromCharCode(0xE4, 0x20AC) + ' +/@*_-.')"),
    ("str:unescape", "expr", "unescape('%E4%u20AC%zz%u12')"),
    (
        "str:encodeURIComponent",
        "expr",
        'encodeURIComponent(String.fromCharCode(0xA7, 0xE4, 0x20AC) + " ;/?:@&=+$,#-_.!~*\'()")',
    ),
    (
        "str:encodeURI",
        "expr",
        'encodeURI("http://a/b c?d=e&f#g;" + String.fromCharCode(0xE4))',
    ),
    (
        "str:decodeURI",
        "expr",
        "decodeURI('%3B%2F%41') + '|' + decodeURIComponent('%3B%2F%41%C3%A4')",
    ),
    (
        "str:lone surrogate encode",
        "body",
        "try { return encodeURIComponent(String.fromCharCode(0xD800)); } catch (e) { return e.name + '|' + e.message + '|' + e.number; }",
    ),
    (
        "str:trim regex",
        "expr",
        "'[' + ' \\u00a0\\t a b \\u3000\\ufeff'.replace(/^\\s+|\\s+$/g, '') + ']'",
    ),
    (
        "str:regex \\s class",
        "body",
        "var c = [0x9, 0xa, 0xb, 0xc, 0xd, 0x20, 0xa0, 0x1680, 0x2000, 0x2028, 0x202f, 0x3000, 0xfeff, 0x85]; var r = []; for (var i = 0; i < c.length; i++) r.push(/\\s/.test(String.fromCharCode(c[i])) ? 1 : 0); return r.join('');",
    ),
    (
        "str:regex \\w \\d \\b",
        "body",
        "var r = []; var c = [0xe4, 0x5f, 0x660, 0x31]; for (var i = 0; i < c.length; i++) { var s = String.fromCharCode(c[i]); r.push((/\\w/.test(s) ? 1 : 0) + '' + (/\\d/.test(s) ? 1 : 0)); } return r.join(',') + '|' + /\\bb/.test('\\u00e4b');",
    ),
    (
        "str:regex dot",
        "expr",
        "[/./.test('\\n'), /./.test('\\r'), /./.test('\\u2028'), /./.test('\\u0085')].join(',')",
    ),
    (
        "str:regex case insensitive",
        "expr",
        "[/\\u00e4/i.test('\\u00c4'), /k/i.test('\\u212a'), /\\u017f/i.test('s')].join(',')",
    ),
    (
        "str:regex backref",
        "expr",
        "[/(a)\\1/.test('aa'), /\\1(a)/.exec('aa')[0], /(a)|\\1b/.exec('b')[0]].join(',')",
    ),
    ("str:regex lookahead", "expr", "/a(?=b)/.exec('ab')[0] + /a(?!b)/.test('ab')"),
    ("str:regex nongreedy", "expr", "/a+?/.exec('aaa')[0]"),
    ("str:regex brackets", "expr", "[/[]/.test('a'), /[^]/.test('a')].join(',')"),
    (
        "str:regex exec groups",
        "body",
        "var m = /(a)|(b)/.exec('b'); return [typeof m[1], m[1], m[2], m.index, m.input, m.length].join('|');",
    ),
    (
        "str:regex lastIndex",
        "body",
        "var r = /a/g; var o = [r.test('aa'), r.lastIndex, r.test('aa'), r.lastIndex, r.test('aa'), r.lastIndex]; return o.join(',');",
    ),
    (
        "str:regex literal shared",
        "body",
        "var out = []; for (var i = 0; i < 2; i++) { var r = /a/g; out.push(r.test('a')); } return out.join(',');",
    ),
    (
        "str:regex static props",
        "body",
        "/(b)(c)/.exec('abcd'); return [RegExp.$1, RegExp.$2, RegExp.$3, RegExp.lastMatch, RegExp.leftContext, RegExp.rightContext, RegExp.input, RegExp.index, RegExp.lastIndex, RegExp.lastParen].join('|');",
    ),
    (
        "str:regex static after replace",
        "body",
        "'xay'.replace(/(a)/, 'b'); return RegExp.$1 + '|' + RegExp.lastMatch;",
    ),
    (
        "str:regex static after test",
        "body",
        "/(q)/.test('aqa'); return RegExp.$1 + '|' + RegExp.index;",
    ),
    (
        "str:regex toString",
        "expr",
        "String(/a\\/b/gi) + '|' + String(new RegExp('a/b')) + '|' + String(new RegExp(''))",
    ),
    (
        "str:regex source",
        "expr",
        "new RegExp('a/b').source + '|' + /x/g.global + '|' + /x/.ignoreCase",
    ),
    (
        "str:regex compile",
        "body",
        "var r = /a/; r.compile('b', 'g'); return r.source + r.global;",
    ),
    (
        "str:RegExp call",
        "body",
        "var r = /a/; return (RegExp(r) === r) + '|' + (new RegExp(r) === r);",
    ),
    (
        "str:String object",
        "expr",
        "typeof new String('a') + '|' + (new String('a') == 'a') + '|' + new String('ab').length",
    ),
    ("str:multiline literal", "expr", "'a\\\nb'"),
    ("str:unicode escape id", "body", "var \\u0061bc = 1; return abc;"),
    ("str:vertical tab escape", "expr", "'\\v'.charCodeAt(0)"),
    (
        "str:string comparison",
        "expr",
        "['a' < 'B', 'a' < 'b', '\\u00e4' < 'b', '10' < '9'].join(',')",
    ),
    # arrays
    ("arr:trailing comma", "expr", "[1, 2,].length"),
    (
        "arr:trailing comma nested",
        "expr",
        "[[1,], [,]].join('|') + '#' + [[1,].length, [,].length, [,,].length].join(',')",
    ),
    (
        "arr:holes",
        "expr",
        "[1,,3].length + '|' + (1 in [1,,3]) + '|' + [1,,3].join('-')",
    ),
    (
        "arr:sort default",
        "expr",
        "[10, 9, 1, 'b', 'a', undefined, 2, null, 'B'].sort().join(',')",
    ),
    (
        "arr:sort holes",
        "body",
        "var a = [3,,1,undefined,2]; a.sort(); return a.length + '|' + a.join(',') + '|' + (4 in a);",
    ),
    (
        "arr:sort stable",
        "body",
        "var a = []; for (var i = 0; i < 24; i++) a.push({k: i % 3, i: i}); a.sort(function (x, y) { return x.k - y.k; }); var r = []; for (var j = 0; j < a.length; j++) r.push(a[j].i); return r.join(',');",
    ),
    (
        "arr:sort inconsistent",
        "body",
        "var a = [5, 1, 4, 2, 3, 9, 7]; a.sort(function () { return 1; }); return a.join(',');",
    ),
    (
        "arr:sort bool comparator",
        "body",
        "var a = [3, 1, 2, 5, 4]; a.sort(function (x, y) { return x > y; }); return a.join(',');",
    ),
    (
        "arr:sort comparator undefined",
        "body",
        "var a = ['b', 'a']; a.sort(undefined); return a.join(',');",
    ),
    (
        "arr:sort large",
        "body",
        "var a = []; for (var i = 0; i < 50; i++) a.push((i * 7919) % 101); a.sort(function (x, y) { return (x % 10) - (y % 10); }); return a.join(',');",
    ),
    (
        "arr:splice one arg",
        "body",
        "var a = [1, 2, 3]; var r = a.splice(1); return a.length + '|' + r.length;",
    ),
    (
        "arr:splice variants",
        "body",
        "var a = [1, 2, 3, 4]; var r1 = a.splice(-2, 1); var r2 = a.splice(1, 0, 9, 8); var r3 = a.splice(); return [a.join(','), r1.join(','), r2.length, r3.length].join('|');",
    ),
    (
        "arr:splice undefined count",
        "body",
        "var a = [1, 2, 3]; var r = a.splice(1, undefined); return a.length + '|' + r.length;",
    ),
    (
        "arr:unshift return",
        "body",
        "var a = [1]; return a.unshift(0) + '|' + a.join(',');",
    ),
    ("arr:push return", "body", "var a = []; return a.push(1, 2) + '|' + a.length;"),
    (
        "arr:concat",
        "expr",
        "[1].concat(2, [3, [4]], 'x').length + '|' + [].concat.call('ab', 1).length",
    ),
    (
        "arr:join",
        "expr",
        "[null, undefined, 1, [2, [3, null]]].join('-') + '|' + [1, 2].join(undefined) + '|' + [1, 2].join()",
    ),
    (
        "arr:slice",
        "expr",
        "[1, 2, 3, 4].slice(-2).join(',') + '|' + [1, 2, 3].slice(1, -1).join(',') + '|' + [1, 2].slice().length",
    ),
    (
        "arr:reverse holes",
        "body",
        "var a = [1,,3]; a.reverse(); return a.length + '|' + (1 in a) + '|' + a.join(',');",
    ),
    (
        "arr:length set",
        "body",
        "var a = [1, 2, 3]; a.length = 1; a[5] = 1; return a.length + '|' + a.join(',');",
    ),
    (
        "arr:Array ctor",
        "expr",
        "[Array(3).length, new Array(2, 3).length, Array('3').length, new Array(3).join('-')].join('|')",
    ),
    (
        "arr:toString",
        "expr",
        "String([1, [2, 3]]) + '|' + String([]) + '|' + [1, 2].toLocaleString()",
    ),
    ("arr:shift empty", "expr", "typeof [].shift() + '|' + typeof [].pop()"),
    (
        "arr:arguments",
        "body",
        "function f() { return [arguments.length, typeof arguments, arguments instanceof Array, typeof arguments.callee].join(','); } return f(1, 2);",
    ),
    (
        "arr:arguments alias",
        "expr",
        "(function (a) { arguments[0] = 9; return a; })(1)",
    ),
    (
        "arr:large index",
        "body",
        "var a = []; a[4294967295] = 1; a[4294967294] = 2; return a.length;",
    ),
    # objects and functions
    (
        "obj:toString null",
        "expr",
        "Object.prototype.toString.call(null) + '|' + Object.prototype.toString.call(undefined) + '|' + Object.prototype.toString.call([])",
    ),
    (
        "obj:toString misc",
        "expr",
        "Object.prototype.toString.call(new Date(0)) + Object.prototype.toString.call(/a/) + Object.prototype.toString.call(function () {}) + Object.prototype.toString.call(arguments) + Object.prototype.toString.call(new Error('x'))",
    ),
    (
        "obj:for-in order",
        "body",
        "var o = {b: 1, a: 2, 2: 3, 1: 4, '-1': 5, '01': 6}; var k = []; for (var x in o) k.push(x); return k.join(',');",
    ),
    (
        "obj:for-in array",
        "body",
        "var a = [5, 6]; a.x = 1; var k = []; for (var x in a) k.push(x); return k.join(',');",
    ),
    (
        "obj:for-in delete",
        "body",
        "var o = {a: 1, b: 2, c: 3}; var k = []; for (var x in o) { k.push(x); delete o.b; } return k.join(',');",
    ),
    (
        "obj:for-in add",
        "body",
        "var o = {a: 1}; var k = []; for (var x in o) { k.push(x); if (k.length < 5) o['z' + k.length] = 1; } return k.join(',');",
    ),
    (
        "obj:for-in string",
        "body",
        "var k = []; for (var x in 'ab') k.push(x); return k.join(',');",
    ),
    (
        "obj:for-in shadow",
        "body",
        "var o = {toString: 1, valueOf: 2, hasOwnProperty: 3, x: 4}; var k = []; for (var p in o) k.push(p); return k.join(',');",
    ),
    (
        "obj:for-in proto",
        "body",
        "function C() { this.a = 1; } C.prototype.b = 2; var k = []; for (var p in new C()) k.push(p); return k.join(',');",
    ),
    (
        "obj:hasOwnProperty",
        "expr",
        "({a: 1}).hasOwnProperty('a') + '|' + 'ab'.hasOwnProperty('length') + '|' + 'ab'.hasOwnProperty(0)",
    ),
    (
        "obj:propertyIsEnumerable",
        "expr",
        "[].propertyIsEnumerable('length') + '|' + ({a: 1}).propertyIsEnumerable('a')",
    ),
    (
        "obj:typeof",
        "expr",
        "[typeof null, typeof function () {}, typeof /x/, typeof new Date(), typeof Math, typeof undefined, typeof NaN, typeof new Boolean(false)].join('|')",
    ),
    (
        "obj:equality",
        "expr",
        "[null == undefined, '1' == 1, '0' == false, NaN == NaN, [] == '', [0] == false, null == 0, ' \\t' == 0, new String('a') == new String('a')].join(',')",
    ),
    (
        "obj:fn toString",
        "expr",
        "String(function  foo ( a,b ) { /* c */ return a+b; })",
    ),
    (
        "obj:fn length name",
        "expr",
        "(function (a, b) {}).length + '|' + (function foo() {}).name",
    ),
    (
        "obj:fn decl in block",
        "program",
        "function probe() { if (false) { function h() { return 1; } } return typeof h; }",
    ),
    (
        "obj:fn decl in block order",
        "program",
        "function probe() { if (true) { function q() { return 1; } } else { function q() { return 2; } } return q(); }",
    ),
    (
        "obj:fn decl in block global",
        "program",
        "if (false) { function gblk() { return 1; } } function probe() { return typeof gblk; }",
    ),
    (
        "obj:fn decl in try",
        "program",
        "function probe() { try { function t() { return 'a'; } } catch (e) {} return t(); }",
    ),
    (
        "obj:NFE leak",
        "program",
        "function probe() { var f = function g() { return 1; }; return typeof g + '|' + (f === g); }",
    ),
    (
        "obj:NFE leak global",
        "program",
        "var gf = function gnfe() { return 1; }; function probe() { return typeof gnfe; }",
    ),
    (
        "obj:NFE hoisted",
        "program",
        "function probe() { var t = typeof h2; var f = function h2() {}; return t; }",
    ),
    (
        "obj:NFE in call",
        "program",
        "function probe() { (function inner() {}); return typeof inner; }",
    ),
    (
        "obj:NFE self ref",
        "program",
        "function probe() { var f = function fact(n) { return n <= 1 ? 1 : n * fact(n - 1); }; return f(5); }",
    ),
    ("obj:this in function", "expr", "(function () { return typeof this; })()"),
    (
        "obj:this global",
        "program",
        "var gthis = this; function probe() { return typeof gthis + '|' + (gthis === (function () { return this; })()); }",
    ),
    (
        "obj:global var",
        "program",
        "var gv = 1; function probe() { return typeof gv + '|' + ('gv' in this) + '|' + (function () { return this.gv; })(); }",
    ),
    (
        "obj:implicit global",
        "body",
        "(function () { implicitG77 = 5; })(); return typeof implicitG77;",
    ),
    ("obj:eval var", "body", "eval('var ev = 1'); return typeof ev;"),
    (
        "obj:eval global",
        "body",
        "var e = eval; e('var evg77 = 1'); return typeof evg77;",
    ),
    (
        "obj:eval return",
        "expr",
        "eval('1; 2;') + '|' + eval('if (true) 3;') + '|' + typeof eval('')",
    ),
    (
        "obj:with",
        "body",
        "var o = {a: 1}; with (o) { a = 2; b77 = 3; } return o.a + '|' + typeof b77 + '|' + typeof o.b77;",
    ),
    (
        "obj:labels",
        "body",
        "var r = 0; outer: for (var i = 0; i < 3; i++) { for (var j = 0; j < 3; j++) { if (j == 1) continue outer; if (i == 2) break outer; r++; } } return r;",
    ),
    (
        "obj:switch",
        "body",
        "var r = ''; switch (2) { case 1: r += 'a'; case 2: r += 'b'; default: r += 'd'; case 3: r += 'c'; } return r;",
    ),
    (
        "obj:switch strict",
        "expr",
        "(function (x) { switch (x) { case '1': return 's'; case 1: return 'n'; } })(1)",
    ),
    (
        "obj:try finally return",
        "expr",
        "(function () { try { return 1; } finally { return 2; } })()",
    ),
    (
        "obj:try finally throw",
        "body",
        "try { try { throw new Error('a'); } finally { var x = 1; } } catch (e) { return e.message + x; }",
    ),
    (
        "obj:catch scope",
        "body",
        "var e = 1; try { throw 2; } catch (e) { var e = 3; } return e;",
    ),
    ("obj:catch var leak", "body", "try { throw 2; } catch (cv) { } return typeof cv;"),
    ("obj:getter on object", "body", "var o = {}; return typeof o.__defineGetter__;"),
    ("obj:proto", "expr", "typeof ({}).__proto__"),
    (
        "obj:constructor",
        "expr",
        "[].constructor === Array && ({}).constructor === Object",
    ),
    (
        "obj:instanceof",
        "expr",
        "[[] instanceof Object, (function () {}) instanceof Function, /a/ instanceof RegExp].join(',')",
    ),
    (
        "obj:new Function",
        "expr",
        "new Function('a', 'b', 'return a + b')(1, 2) + '|' + String(new Function('a', 'return a'))",
    ),
    (
        "obj:Function arguments prop",
        "body",
        "function f() { return typeof f.arguments; } return f();",
    ),
    (
        "obj:Boolean object",
        "expr",
        "(new Boolean(false) ? 'truthy' : 'falsy') + '|' + String(new Boolean(false))",
    ),
    (
        "obj:valueOf order",
        "body",
        "var log = []; var o = {valueOf: function () { log.push('v'); return 1; }, toString: function () { log.push('s'); return 'x'; }}; var r = [o + '', String(o), o * 1, '' + o]; return r.join(',') + '|' + log.join('');",
    ),
    ("obj:Date compare", "body", "var d = new Date(0); return (d + 1).length > 5;"),
    ("obj:octal string", "expr", "'\\08'.length + '|' + '\\0'.charCodeAt(0)"),
    (
        "obj:comma property",
        "expr",
        "({1.5: 'a', 1e3: 'b', 0x10: 'c'})['1.5'] + ({1e3: 'b'})['1000'] + ({0x10: 'c'})['16']",
    ),
    (
        "obj:delete array",
        "body",
        "var a = [1, 2]; delete a[0]; return a.length + '|' + (0 in a);",
    ),
    ("obj:void", "expr", "typeof void 0"),
    ("obj:conditional comp", "expr", "/*@cc_on 1 + @*/ 0"),
    (
        "obj:conditional comp vars",
        "body",
        "var r = 'none'; /*@cc_on r = @_jscript_version; @*/ return r;",
    ),
    ("obj:debugger", "body", "debugger; return 1;"),
    ("obj:html comment", "body", "var x = 1;\n<!-- comment\nreturn x;"),
    ("obj:get as identifier", "body", "var get = 1, set = 2; return get + set;"),
    ("obj:ASI return", "body", "return\n1;"),
    ("obj:ASI ++", "body", "var a = 1, b = 2;\na\n++\nb\nreturn a + '|' + b;"),
    # dates
    ("date:local jan", "expr", "new Date(2026, 0, 2).getTime()"),
    ("date:local jul", "expr", "new Date(2026, 6, 2).getTime()"),
    (
        "date:tz offset",
        "expr",
        "new Date(2026, 0, 2).getTimezoneOffset() + '|' + new Date(2026, 6, 2).getTimezoneOffset() + '|' + new Date(1990, 6, 2).getTimezoneOffset() + '|' + new Date(1970, 6, 2).getTimezoneOffset()",
    ),
    (
        "date:dst gap",
        "expr",
        "new Date(2026, 2, 29, 2, 30).getTime() + '|' + new Date(2026, 2, 29, 2, 30).getHours()",
    ),
    (
        "date:dst overlap",
        "expr",
        "new Date(2026, 9, 25, 2, 30).getTime() + '|' + new Date(2026, 9, 25, 2, 30).getTimezoneOffset()",
    ),
    (
        "date:toString",
        "expr",
        "new Date(2026, 0, 2, 3, 4, 5).toString() + '#' + new Date(2026, 6, 12, 13, 14, 15).toString()",
    ),
    (
        "date:toString neg year",
        "expr",
        "new Date(-100, 0, 1).toString() + '#' + new Date(50, 0, 1).getFullYear()",
    ),
    (
        "date:toDateString",
        "expr",
        "new Date(2026, 0, 2, 3, 4, 5).toDateString() + '#' + new Date(2026, 11, 31).toDateString()",
    ),
    ("date:toTimeString", "expr", "new Date(2026, 0, 2, 3, 4, 5).toTimeString()"),
    (
        "date:toUTCString",
        "expr",
        "new Date(Date.UTC(2026, 0, 2, 3, 4, 5)).toUTCString() + '#' + new Date(Date.UTC(2026, 0, 2)).toGMTString()",
    ),
    (
        "date:toLocaleString",
        "expr",
        "new Date(2026, 0, 2, 3, 4, 5).toLocaleString() + '#' + new Date(2026, 6, 12, 13, 14, 15).toLocaleString()",
    ),
    (
        "date:toLocaleDateString",
        "expr",
        "new Date(2026, 0, 2, 3, 4, 5).toLocaleDateString() + '#' + new Date(2026, 4, 20).toLocaleDateString()",
    ),
    (
        "date:toLocaleTimeString",
        "expr",
        "new Date(2026, 0, 2, 3, 4, 5).toLocaleTimeString() + '#' + new Date(2026, 0, 2, 13, 4, 5).toLocaleTimeString()",
    ),
    ("date:Date() call", "expr", "typeof Date() + '|' + (Date().length > 10)"),
    (
        "date:parse formats",
        "expr",
        "[Date.parse('2026/01/02'), Date.parse('Jan 2, 2026'), Date.parse('January 2, 2026 10:00:00'), Date.parse('2026-01-02'), Date.parse('1/2/2026'), Date.parse('Fri Jan 2 03:04:05 UTC+0100 2026'), Date.parse('Fri, 2 Jan 2026 03:04:05 UTC'), Date.parse('2 Jan 2026'), Date.parse('Jan 2 2026 10:00 PM'), Date.parse('2026-01-02T10:00:00Z'), Date.parse('garbage'), Date.parse('Fri Jan 02 2026 03:04:05 GMT+0200')].join(',')",
    ),
    (
        "date:parse more",
        "expr",
        "[Date.parse('01/02/2026 13:30'), Date.parse('2026/1/2 1:2:3'), Date.parse('Jan 2, 2026 UTC'), Date.parse('Jan 2, 2026 GMT+0300'), Date.parse('Jan 2, 2026 EST'), Date.parse('12/31/99'), Date.parse('Monday, January 5, 2026')].join(',')",
    ),
    (
        "date:new Date string",
        "expr",
        "new Date('2026/03/04 05:06:07').getTime() + '|' + new Date('Mar 4 2026').getDate()",
    ),
    (
        "date:getYear",
        "expr",
        "[new Date(2026, 0, 2).getYear(), new Date(1999, 0, 2).getYear(), new Date(1899, 0, 2).getYear(), new Date(1900, 0, 2).getYear()].join(',')",
    ),
    (
        "date:setYear",
        "body",
        "var d = new Date(2026, 0, 2); d.setYear(98); var a = d.getFullYear(); d.setYear(2010); return a + '|' + d.getFullYear();",
    ),
    (
        "date:setters overflow",
        "body",
        "var d = new Date(2026, 0, 31); d.setMonth(1); var a = d.getDate() + '/' + d.getMonth(); d.setHours(25); return a + '|' + d.getDate() + ' ' + d.getHours();",
    ),
    (
        "date:setters return",
        "body",
        "var d = new Date(2026, 0, 1); return [d.setDate(2), d.setFullYear(2025, 5), d.setMinutes(61)].join(',');",
    ),
    (
        "date:invalid",
        "body",
        "var d = new Date(NaN); return [d.getTime(), d.getFullYear(), d.toString(), d.toUTCString(), d.toLocaleString()].join('|');",
    ),
    (
        "date:UTC",
        "expr",
        "[Date.UTC(2026, 0), Date.UTC(2026), Date.UTC(99, 0, 1), Date.UTC(2026, 13, 40)].join(',')",
    ),
    (
        "date:2-digit year ctor",
        "expr",
        "new Date(99, 0, 1).getFullYear() + '|' + new Date(100, 0, 1).getFullYear()",
    ),
    (
        "date:string concat",
        "body",
        "var d = new Date(2026, 0, 2, 3, 4, 5); return '' + d;",
    ),
    ("date:valueOf arithmetic", "expr", "new Date(2026, 0, 2) - new Date(2026, 0, 1)"),
    (
        "date:getDay",
        "expr",
        "new Date(2026, 0, 2).getDay() + '|' + new Date(Date.UTC(2026, 0, 2, 23, 30)).getUTCDay()",
    ),
    (
        "date:millisecond fraction",
        "expr",
        "new Date(1.7).getTime() + '|' + new Date(-1.7).getTime()",
    ),
    (
        "date:max",
        "expr",
        "new Date(8.64e15).getTime() + '|' + new Date(8.64e15 + 1).getTime()",
    ),
    (
        "date:month names",
        "body",
        "var r = []; for (var m = 0; m < 12; m++) r.push(new Date(2026, m, 15).toString().substr(4, 3)); return r.join(',');",
    ),
    (
        "date:day names",
        "body",
        "var r = []; for (var d = 4; d < 11; d++) r.push(new Date(2026, 0, d).toString().substr(0, 3)); return r.join(',');",
    ),
    (
        "date:local midnight",
        "expr",
        "new Date(2026, 9, 25).getTime() + '|' + new Date(2026, 2, 29).getTime()",
    ),
    # misc runtime
    (
        "misc:Enumerator array",
        "body",
        "try { var e = new Enumerator([1, 2]); var r = []; for (; !e.atEnd(); e.moveNext()) r.push(e.item()); return r.join(','); } catch (x) { return x.name + '|' + x.message + '|' + x.number; }",
    ),
    (
        "misc:VBArray",
        "body",
        "try { new VBArray([1]); return 'ok'; } catch (x) { return x.name + '|' + x.message + '|' + x.number; }",
    ),
    (
        "misc:ActiveXObject",
        "body",
        "try { new ActiveXObject('No.Such.Object'); return 'ok'; } catch (x) { return x.name + '|' + x.message + '|' + x.number; }",
    ),
    (
        "misc:GetObject",
        "body",
        "try { GetObject('x'); return 'ok'; } catch (x) { return x.name + '|' + x.message + '|' + x.number; }",
    ),
    ("misc:CollectGarbage", "expr", "typeof CollectGarbage()"),
    (
        "misc:Debug",
        "body",
        "return typeof Debug + '|' + typeof Debug.write + '|' + typeof Debug.writeln;",
    ),
    (
        "misc:getVarDate",
        "body",
        "var v = new Date(2026, 0, 2).getVarDate(); return typeof v + '|' + String(v);",
    ),
    ("misc:undefined assign", "body", "undefined = 1; return typeof undefined;"),
    ("misc:NaN assign", "body", "NaN = 1; return NaN;"),
    (
        "misc:recursion depth",
        "body",
        "function r(n) { return n === 0 ? 0 : 1 + r(n - 1); } return r(5000);",
    ),
    ("misc:string concat number", "expr", "'x' + 1.0 + '|' + 0.1 * 3 + '|' + 1 / 3"),
    ("misc:Math.random type", "expr", "typeof Math.random()"),
    ("misc:new Date type", "expr", "typeof new Date().getTime()"),
    (
        "misc:function hoisting",
        "program",
        "function probe() { return typeof later; function later() {} }",
    ),
    (
        "misc:var hoisting",
        "program",
        "function probe() { var r = typeof v1; var v1 = 1; return r; }",
    ),
    (
        "misc:duplicate function",
        "program",
        "function dup() { return 1; } function dup() { return 2; } function probe() { return dup(); }",
    ),
    (
        "misc:global function this",
        "program",
        "function gf2() { return this === undefined ? 'u' : typeof this; } function probe() { return gf2(); }",
    ),
]


_COMPILE: list[tuple[str, str]] = [
    ("getter", "var o = {get x() { return 1; }};"),
    ("setter", "var o = {set x(v) {}};"),
    ("reserved prop class", "var o = {class: 1};"),
    ("reserved member class", "var o = {}; o.class = 1;"),
    ("keyword prop if", "var o = {if: 1};"),
    ("keyword member default", "var o = {}; o.default = 1;"),
    ("keyword member delete", "var o = {}; o['delete'](); o.delete();"),
    ("future reserved enum", "var enum = 1;"),
    ("future reserved int", "var int = 1;"),
    ("future reserved abstract", "var abstract = 1;"),
    ("future reserved class var", "var class = 1;"),
    ("future reserved super", "var super = 1;"),
    ("let", "let a = 1;"),
    ("const", "const a = 1;"),
    ("arrow", "var f = x => x;"),
    ("template", "var s = `a`;"),
    ("class decl", "class A {}"),
    ("spread", "f(...a);"),
    ("default param", "function f(a = 1) {}"),
    ("destructuring", "var {a} = {};"),
    ("for-of", "for (var x of []) {}"),
    ("object trailing comma", "var o = {a: 1,};"),
    ("array trailing comma", "var a = [1,];"),
    ("call trailing comma", "f(1,);"),
    ("param trailing comma", "function f(a,) {}"),
    ("param list brace", "function f( {}"),
    ("param list brace after comma", "function f(a, {}"),
    ("param list anonymous brace", "var f = function ( {};"),
    ("param list number", "function f(1) {}"),
    ("param list unterminated", "var a = 1;\nfunction f( {\n"),
    ("regex flag y", "var r = /a/y;"),
    ("regex flag u", "var r = /a/u;"),
    ("regex flag s", "var r = /a/s;"),
    ("regex flags gim", "var r = /a/gim;"),
    ("regex duplicate flag", "var r = /a/gg;"),
    ("regex invalid", "var r = /(/;"),
    ("regex slash in class", "var r = /[/]/;"),
    ("debugger", "debugger;"),
    ("octal literal", "var a = 010;"),
    ("octal escape", "var a = '\\101';"),
    ("unicode escape id", "var \\u0061 = 1;"),
    ("html comment", "<!-- x\nvar a = 1;"),
    ("conditional compilation", "/*@cc_on var a = 1; @*/"),
    ("get as name", "var get = 1, set = 2;"),
    ("function in expression stmt", "function f() {}();"),
    ("iife", "(function () {})();"),
    ("label", "a: for (;;) { break a; }"),
    ("with", "with ({}) {}"),
    ("getter via defineGetter call", "o.__defineGetter__('x', function () {});"),
    ("strict directive", "'use strict'; var a = 1;"),
    ("keyword as label", "default: 1;"),
    ("number dot", "var a = 1..toString(); var b = 1.e3;"),
    ("unterminated string", "var a = 'x;"),
    ("unterminated comment", "/* x"),
    ("missing paren", "if (a { }"),
    ("lone else", "else {}"),
    ("return at top", "return 1;"),
    ("break outside loop", "break;"),
    ("continue in switch", "switch (1) { case 1: continue; }"),
    ("duplicate param", "function f(a, a) {}"),
    ("duplicate prop", "var o = {a: 1, a: 2};"),
    ("line terminator in string", "var a = 'x\u2028y';"),
    ("utf bom", "\ufeffvar a = 1;"),
    ("nbsp whitespace", "var\u00a0a = 1;"),
    ("zero-width in id", "var a\u200c = 1;"),
    ("unicode id", "var äb = 1;"),
    ("getter keyword object", "var o = {get: 1, set: 2};"),
    ("try without catch", "try {} finally {}"),
    ("catch without param", "try {} catch {}"),
    ("exponent operator", "var a = 2 ** 3;"),
    ("in operator for-in var init", "for (var i = 0 in {}) {}"),
    ("asi object", "var a = 1\n(function () {})"),
]


_WORDS = [
    "abstract",
    "boolean",
    "byte",
    "char",
    "class",
    "const",
    "debugger",
    "double",
    "enum",
    "export",
    "extends",
    "final",
    "float",
    "goto",
    "implements",
    "import",
    "int",
    "interface",
    "let",
    "long",
    "native",
    "package",
    "private",
    "protected",
    "public",
    "short",
    "static",
    "super",
    "synchronized",
    "throws",
    "transient",
    "volatile",
    "yield",
    "await",
    "eval",
    "arguments",
    "get",
    "set",
    "of",
    "async",
    "undefined",
    "NaN",
    "Infinity",
    "null",
    "true",
    "false",
    "this",
    "void",
    "typeof",
    "instanceof",
    "in",
    "delete",
    "new",
    "function",
    "var",
    "if",
    "else",
    "for",
    "while",
    "do",
    "return",
    "switch",
    "case",
    "default",
    "break",
    "continue",
    "throw",
    "try",
    "catch",
    "finally",
    "with",
]


def _reserved() -> list[Probe]:
    probes: list[Probe] = []
    for w in _WORDS:
        probes.append(Probe(f"compile:var {w}", "compile", f"var {w} = 1;"))
        probes.append(
            Probe(f"compile:member {w}", "compile", f"var o = {{}}; o.{w} = 1;")
        )
        probes.append(Probe(f"compile:key {w}", "compile", f"var o = {{{w}: 1}};"))
        probes.append(Probe(f"compile:fn {w}", "compile", f"function {w}() {{}}"))
    return probes


_EXTRA: list[tuple[str, str, str]] = [
    (
        "err:number typeof",
        "expr",
        "typeof new Error('m').number + '|' + typeof new Error().number + '|' + typeof new Error(5).number + '|' + typeof new TypeError('t').number",
    ),
    (
        "err:number values",
        "expr",
        "[new Error('m').number, new Error().number, new Error(5).number, new Error(5).message, new Error('5').number, new Error(5, 6).message, new Error(5, 6).description, new TypeError('t').number].join('|')",
    ),
    (
        "err:own keys",
        "body",
        "var e = new Error('m'); var k = []; for (var p in e) k.push(p + '=' + e[p]); return k.join(',');",
    ),
    (
        "err:caught own keys",
        "body",
        "try { null.x; } catch (e) { var k = []; for (var p in e) k.push(p); return k.join(',') + '|' + e.hasOwnProperty('message') + e.hasOwnProperty('number') + e.hasOwnProperty('description'); }",
    ),
    (
        "err:name assign",
        "body",
        "var e = new Error('m'); e.name = 'X'; return String(e) + '|' + e.name;",
    ),
    (
        "err:prototype props",
        "expr",
        "Error.prototype.message + '|' + Error.prototype.name + '|' + typeof Error.prototype.description + '|' + typeof Error.prototype.number",
    ),
    (
        "err:subclass",
        "body",
        "var e = new RangeError('r'); return [e.name, e.message, e.number, e instanceof Error, String(e)].join('|');",
    ),
    (
        "err:EvalError URIError",
        "expr",
        "new EvalError('a').name + new URIError('b').name + new SyntaxError('c').name",
    ),
    (
        "err:apply null",
        "expr",
        "(function () { return arguments.length; }).apply(null, null) + '|' + (function () { return arguments.length; }).apply(null, undefined)",
    ),
    (
        "err:apply arguments",
        "expr",
        "(function () { return (function () { return arguments.length; }).apply(null, arguments); })(1, 2, 3)",
    ),
    (
        "err:call this primitive",
        "expr",
        "(function () { return typeof this; }).call(5) + '|' + (function () { return typeof this; }).call(null)",
    ),
    (
        "err:Date call on non-date",
        "body",
        "try { Date.prototype.getTime.call({}); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:toString on non-number",
        "body",
        "try { Number.prototype.toString.call('x'); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:regex compile in ctor",
        "body",
        "try { new RegExp('a', 'x'); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:undefined method on number",
        "body",
        "try { (5).foo(); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:undefined method on string",
        "body",
        "try { 'x'.foo(); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:method of undefined var prop",
        "body",
        "var o = {}; try { o.a.b(); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:call result",
        "body",
        "function f() { return 1; } try { f()(); } catch (e) { return [e.name, e.message, e.number].join('|'); }",
    ),
    (
        "err:assign undeclared in fn",
        "body",
        "(function () { undeclaredZ9 = 1; })(); return typeof undeclaredZ9;",
    ),
    (
        "err:throw in finally",
        "body",
        "try { try { throw 1; } finally { throw 2; } } catch (e) { return e; }",
    ),
    (
        "err:catch param leak value",
        "body",
        "var r; try { throw 7; } catch (q9) { } r = q9; return r;",
    ),
    (
        "err:catch modify outer",
        "body",
        "var e = 'outer'; try { throw 'inner'; } catch (e) { } return e;",
    ),
    (
        "err:nested catch same name",
        "body",
        "try { throw 1; } catch (e) { try { throw 2; } catch (e) { } return e; }",
    ),
    (
        "sort:calls 6",
        "body",
        "var log = []; [5, 3, 8, 1, 9, 2].sort(function (a, b) { log.push(a + '' + b); return a - b; }); return log.join(',');",
    ),
    (
        "sort:calls 10",
        "body",
        "var log = []; var a = [10, 1, 9, 2, 8, 3, 7, 4, 6, 5]; a.sort(function (x, y) { log.push(x + ':' + y); return x - y; }); return a.join(',') + '#' + log.join(',');",
    ),
    (
        "sort:calls sorted",
        "body",
        "var log = []; [1, 2, 3, 4, 5].sort(function (a, b) { log.push(a + '' + b); return a - b; }); return log.join(',');",
    ),
    (
        "sort:calls reversed",
        "body",
        "var log = []; [5, 4, 3, 2, 1].sort(function (a, b) { log.push(a + '' + b); return a - b; }); return log.join(',');",
    ),
    (
        "sort:calls 2",
        "body",
        "var log = []; [2, 1].sort(function (a, b) { log.push(a + '' + b); return a - b; }); return log.join(',');",
    ),
    (
        "sort:calls 3",
        "body",
        "var log = []; [3, 1, 2].sort(function (a, b) { log.push(a + '' + b); return a - b; }); return log.join(',');",
    ),
    (
        "sort:calls 17",
        "body",
        "var log = []; var a = []; for (var i = 0; i < 17; i++) a.push((i * 7) % 17); a.sort(function (x, y) { log.push(x + ':' + y); return x - y; }); return a.join(',') + '#' + log.join(',');",
    ),
    (
        "sort:calls 33",
        "body",
        "var log = 0; var a = []; for (var i = 0; i < 33; i++) a.push((i * 13) % 33); a.sort(function (x, y) { log++; return x - y; }); return a.join(',') + '#' + log;",
    ),
    (
        "sort:random comparator",
        "body",
        "var s = 1; function rnd() { s = (s * 16807) % 2147483647; return s; } var a = []; for (var i = 0; i < 20; i++) a.push(i); a.sort(function () { return (rnd() % 3) - 1; }); return a.join(',');",
    ),
    (
        "sort:nan comparator",
        "body",
        "var a = [3, 1, 2]; a.sort(function () { return NaN; }); return a.join(',');",
    ),
    (
        "sort:string comparator",
        "body",
        "var a = [3, 1, 2]; a.sort(function (x, y) { return '' + (x - y); }); return a.join(',');",
    ),
    (
        "sort:undefined and holes",
        "body",
        "var a = [3, undefined, , 1, null, 'a']; a.sort(); return a.length + '|' + a.join(',') + '|' + (5 in a) + (4 in a);",
    ),
    (
        "sort:comparator with undefined",
        "body",
        "var log = []; var a = [2, undefined, 1]; a.sort(function (x, y) { log.push(x + '' + y); return x - y; }); return a.join(',') + '#' + log.join(',');",
    ),
    (
        "sort:returns",
        "body",
        "var a = [2, 1]; return (a.sort() === a) + '|' + typeof a.sort(function () { return 0; });",
    ),
    (
        "sort:object array",
        "body",
        "var a = {0: 'b', 1: 'a', length: 2}; Array.prototype.sort.call(a); return a[0] + a[1];",
    ),
    (
        "radix:threshold",
        "expr",
        "[(Math.pow(2, 61) - 4096).toString(16), Math.pow(2, 61).toString(16), Math.pow(2, 62).toString(2).length, (1e18).toString(36), (2e18).toString(7), (2.4e18).toString(8)].join('|')",
    ),
    (
        "radix:fractions",
        "expr",
        "[(0.1).toString(7), (0.3).toString(36), (1 / 3).toString(3), (123.456).toString(8), (0.000123).toString(16), (2.5).toString(5), (-0.75).toString(32), (1e-10).toString(2).length].join('|')",
    ),
    (
        "radix:integers",
        "expr",
        "[(123456789).toString(36), (-42).toString(3), (4294967295).toString(16), (9007199254740991).toString(2).length, (1e17).toString(7)].join('|')",
    ),
    (
        "radix:invalid",
        "body",
        "var r = []; var v = [0, 37, 2.5, '16', undefined]; for (var i = 0; i < v.length; i++) { try { r.push((255).toString(v[i])); } catch (e) { r.push(e.name + ':' + e.number); } } return r.join('|');",
    ),
    (
        "num:toFixed args",
        "body",
        "var r = []; var v = [undefined, null, '2', 2.7, -0.5, 20, 21, NaN]; for (var i = 0; i < v.length; i++) { try { r.push((1.25).toFixed(v[i])); } catch (e) { r.push(e.name + ':' + e.number); } } return r.join('|');",
    ),
    (
        "num:toPrecision args",
        "body",
        "var r = []; var v = [undefined, 1, 21, 22, 0.5, '3']; for (var i = 0; i < v.length; i++) { try { r.push((123.456).toPrecision(v[i])); } catch (e) { r.push(e.name + ':' + e.number); } } return r.join('|');",
    ),
    (
        "num:toExponential args",
        "body",
        "var r = []; var v = [undefined, 0, 20, 21, -1]; for (var i = 0; i < v.length; i++) { try { r.push((123.456).toExponential(v[i])); } catch (e) { r.push(e.name + ':' + e.number); } } return r.join('|');",
    ),
    (
        "num:special toFixed",
        "expr",
        "[(NaN).toFixed(2), (Infinity).toFixed(1), (-Infinity).toPrecision(2), (1e-7).toFixed(10), (123.456e30).toFixed(1)].join('|')",
    ),
    (
        "num:string concat forms",
        "body",
        "var x = 1.1 + 2.2; var a = [x + '', '' + x, String(x), x.toString(), [x].join(), [x] + '', 'v=' + x, x + 'v'].join('|'); return a;",
    ),
    (
        "num:concat compound",
        "body",
        "var s = 'a'; s += 0.1 * 3; var o = {p: 'b'}; o.p += 1.1 + 2.2; var q = ['c']; q[0] += 0.7 + 0.1; return s + '|' + o.p + '|' + q[0];",
    ),
    (
        "num:object key",
        "body",
        "var o = {}; o[1.1 + 2.2] = 1; var k = []; for (var p in o) k.push(p); return k.join(',');",
    ),
    (
        "num:parseInt number arg",
        "expr",
        "parseInt(0.0000005) + '|' + parseInt(1e21) + '|' + parseInt(-0.5)",
    ),
    (
        "num:isNaN coercion",
        "expr",
        "[isNaN('0x10'), isNaN('1e5'), isNaN(' 5 '), isNaN('5px')].join(',')",
    ),
    (
        "str:split misc",
        "expr",
        "['a1b2c3'.split(/\\d/, 2).join('|'), 'abc'.split(/b/).length, 'aXbXc'.split('X', 1).join('|'), 'a,b,'.split(',').length, ',a'.split(',').length, 'abc'.split(/(b)?/).join('|'), 'abc'.split('b', undefined).length].join('#')",
    ),
    (
        "str:split regex static",
        "body",
        "'xay'.split(/(a)/); return RegExp.$1 + '|' + RegExp.lastMatch + '|' + RegExp.index;",
    ),
    (
        "str:match static",
        "body",
        "'xay'.match(/(a)/); var r1 = RegExp.$1; 'qzq'.match(/(z)/g); return r1 + '|' + RegExp.$1 + '|' + RegExp.lastMatch + '|' + RegExp.index + '|' + RegExp.lastIndex;",
    ),
    (
        "str:search static",
        "body",
        "'xay'.search(/(a)/); return RegExp.$1 + '|' + RegExp.index;",
    ),
    (
        "str:regex failed match static",
        "body",
        "/(a)/.exec('a'); /(b)/.exec('c'); return RegExp.$1 + '|' + RegExp.lastMatch;",
    ),
    (
        "str:regex $_",
        "body",
        "/(a)/.exec('xa'); return RegExp['$_'] + '|' + RegExp.input + '|' + RegExp['$&'] + '|' + RegExp['$+'] + '|' + RegExp['$`'] + '|' + RegExp[\"$'\"];",
    ),
    (
        "str:regex input assign",
        "body",
        "RegExp.input = 'abc'; return RegExp.input + '|' + RegExp['$_'];",
    ),
    (
        "str:regex global exec loop",
        "body",
        "var r = /(\\d)/g, m, out = []; while ((m = r.exec('a1b2')) !== null) out.push(m[1] + '@' + m.index + '/' + r.lastIndex); return out.join(',');",
    ),
    (
        "str:regex empty match lastIndex",
        "body",
        "var r = /x*/g; var m1 = r.exec('ab'); var l1 = r.lastIndex; var m2 = r.exec('ab'); return l1 + '|' + r.lastIndex + '|' + m1.index + '|' + m2.index;",
    ),
    ("str:replace empty match global", "expr", "'abc'.replace(/x*/g, '-')"),
    ("str:match empty global", "expr", "'abc'.match(/x*/g).length"),
    (
        "str:regex sticky source",
        "expr",
        "/a/gim.source + '|' + /a/gim.global + /a/gim.ignoreCase + /a/gim.multiline",
    ),
    (
        "str:regex vt escape",
        "expr",
        "/\\v/.test('v') + '|' + /\\v/.test(String.fromCharCode(11)) + '|' + /[\\v]/.test('v')",
    ),
    (
        "str:regex \\s in class",
        "expr",
        "/[\\s]/.test(String.fromCharCode(160)) + '|' + /[\\S]/.test(String.fromCharCode(160)) + '|' + /\\S/.test(String.fromCharCode(160))",
    ),
    (
        "str:regex dot class",
        "expr",
        "/a.c/.test('a' + String.fromCharCode(13) + 'c') + '|' + /a.c/.test('a\\nc')",
    ),
    (
        "str:RegExp ctor class",
        "expr",
        "new RegExp('\\\\s').test(String.fromCharCode(160)) + '|' + new RegExp('.').test(String.fromCharCode(13))",
    ),
    (
        "str:hasOwnProperty index",
        "expr",
        "'ab'.hasOwnProperty(0) + '|' + new String('ab').hasOwnProperty(0) + '|' + new String('ab').hasOwnProperty('length')",
    ),
    (
        "str:for-in String object",
        "body",
        "var k = []; for (var p in new String('ab')) k.push(p); return k.join(',');",
    ),
    (
        "str:String() forms",
        "expr",
        "String() + '|' + String(null) + '|' + String(1.1 + 2.2) + '|' + new String(1.1 + 2.2).length + '|' + typeof String(1) + '|' + (new String('a') instanceof String) + '|' + String.prototype.constructor === String",
    ),
    (
        "str:case special",
        "body",
        "var c = [0x149, 0x1f0, 0x390, 0x3b0, 0x587, 0x1e96, 0x1f50, 0xfb06, 0x130, 0x131, 0x17f, 0x1c5, 0x2126, 0x212a, 0x212b]; var r = []; for (var i = 0; i < c.length; i++) { var s = String.fromCharCode(c[i]); r.push(s.toUpperCase().charCodeAt(0).toString(16) + '/' + s.toUpperCase().length + '/' + s.toLowerCase().charCodeAt(0).toString(16)); } return r.join(',');",
    ),
    (
        "fn:toString nfe",
        "program",
        "var f = function g(a) { return a; }; function probe() { return String(f) + '|' + String(g); }",
    ),
    (
        "fn:toString nested",
        "program",
        "function outer() {\n  // comment\n  var x = 1 + 2;\n  return x;\n}\nfunction probe() { return String(outer); }",
    ),
    ("fn:toString builtin", "expr", "String(Math.max).replace(/\\s+/g, ' ')"),
    (
        "fn:toString Function ctor",
        "expr",
        "String(new Function('a', 'b', 'return a + b;')) + '#' + String(new Function())",
    ),
    (
        "fn:arguments.length",
        "expr",
        "(function (a, b) { return arguments.length; })(1) + '|' + (function (a, b) {}).length",
    ),
    (
        "fn:name prop",
        "expr",
        "typeof (function foo() {}).name + '|' + ('name' in function () {})",
    ),
    (
        "fn:apply array-like ok",
        "body",
        "try { return (function () { return arguments.length; }).apply(null, [1, 2]); } catch (e) { return e.message; }",
    ),
    ("cc:basic", "body", "var r = 0; /*@cc_on @*/ /*@ r = 1; @*/ return r;"),
    (
        "cc:if",
        "body",
        "var r = 'x'; /*@cc_on @if (@_jscript_version >= 5) r = 'new'; @else r = 'old'; @end @*/ return r;",
    ),
    (
        "cc:vars",
        "body",
        "var r = []; /*@cc_on r.push(@_jscript, @_win32, @_win64, @_x86, @_amd64, @_microsoft, @_jscript_build, @_mac, @_alpha, @_mc680x0, @_PowerPC); @*/ return r.join(',');",
    ),
    ("cc:set", "body", "var r = 0; /*@cc_on @set @myvar = 3 r = @myvar; @*/ return r;"),
    ("cc:line comment", "body", "var r = 0;\n//@cc_on\n//@ r = 2;\nreturn r;"),
    ("cc:without cc_on", "body", "var r = 0; /*@ r = 1; @*/ return r;"),
    (
        "cc:undefined var",
        "body",
        "var r; /*@cc_on r = @_nosuch; @*/ return typeof r + '|' + r;",
    ),
    (
        "misc:Enumerator methods",
        "body",
        "var e = new Enumerator(['a', 'b']); var r = [e.item()]; e.moveNext(); r.push(e.item(), e.atEnd()); e.moveNext(); r.push(e.atEnd(), typeof e.item()); e.moveFirst(); r.push(e.item()); return r.join('|');",
    ),
    (
        "misc:Enumerator object",
        "body",
        "try { var e = new Enumerator({a: 1}); return e.atEnd() + '|' + e.item(); } catch (x) { return x.name + '|' + x.message + '|' + x.number; }",
    ),
    (
        "misc:Enumerator string",
        "body",
        "try { var e = new Enumerator('ab'); return e.atEnd() + '|' + e.item(); } catch (x) { return x.name + '|' + x.message + '|' + x.number; }",
    ),
    (
        "misc:Debug methods",
        "body",
        "var k = []; for (var p in Debug) k.push(p); return typeof Debug.write + typeof Debug.writeln + typeof Debug.setNonUserCodeExceptions + '|' + k.join(',');",
    ),
    (
        "misc:global this props",
        "body",
        "var k = []; for (var p in this) k.push(p); return k.length + '|' + typeof this.Math + '|' + ('Math' in this) + '|' + this.propertyIsEnumerable('Math');",
    ),
    (
        "misc:global object toString",
        "expr",
        "String(this) + '|' + Object.prototype.toString.call(this)",
    ),
    (
        "misc:undefined global var",
        "body",
        "var u; return typeof u + (u === undefined) + (u == null);",
    ),
    (
        "misc:Math props",
        "expr",
        "[Math.E, Math.LN10, Math.PI, Math.SQRT2, Math.LOG2E].join('|')",
    ),
    (
        "misc:Math funcs",
        "expr",
        "[Math.exp(1), Math.log(10), Math.sin(1), Math.cos(1), Math.tan(1), Math.atan(1), Math.asin(0.5), Math.acos(0.5), Math.pow(2, 0.5), Math.sqrt(2), Math.atan2(1, 2)].join('|')",
    ),
    (
        "misc:Math precision",
        "expr",
        "[Math.pow(10, 22), Math.pow(10, -5), Math.pow(1.1, 10), Math.exp(10), Math.log(2), Math.sin(Math.PI)].join('|')",
    ),
    (
        "misc:Number constants",
        "expr",
        "[Number.MAX_VALUE, Number.MIN_VALUE, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY].join('|')",
    ),
    (
        "misc:Array generic join",
        "expr",
        "Array.prototype.join.call({0: 1.1 + 2.2, 1: 'x', length: 2})",
    ),
    (
        "misc:array toLocaleString",
        "expr",
        "[1234.5, 'a', null, 0.125].toLocaleString()",
    ),
    (
        "misc:date toLocale forms",
        "expr",
        "new Date(2026, 6, 4, 0, 0, 0).toLocaleString() + '#' + new Date(2026, 6, 4).toLocaleDateString() + '#' + new Date(2026, 6, 4, 23, 59, 59).toLocaleTimeString()",
    ),
    (
        "misc:number toLocale forms",
        "expr",
        "[(1e-7).toLocaleString(), (-0.005).toLocaleString(), (1.005).toLocaleString(), (999.995).toLocaleString(), (12345678).toLocaleString(), (-1).toLocaleString()].join(';')",
    ),
]


def _case_mapping_full() -> list[Probe]:
    probes: list[Probe] = []
    for start in range(0x0000, 0x10000, 256):
        if 0xD800 <= start < 0xE000:
            continue
        code = (
            f"var r = []; for (var c = {start}; c < {start + 256}; c++) {{ var s = String.fromCharCode(c); "
            "var u = s.toUpperCase(), l = s.toLowerCase(); "
            "if (u !== s || l !== s) { var v = [c.toString(16), ':']; "
            "for (var i = 0; i < u.length; i++) v.push(u.charCodeAt(i).toString(16)); v.push('/'); "
            "for (var j = 0; j < l.length; j++) v.push(l.charCodeAt(j).toString(16)); r.push(v.join('.')); } } return r.join(',');"
        )
        probes.append(Probe(f"casefull:{start:04x}", "body", code))
    return probes


def _numbers(count: int = 400) -> list[Probe]:
    rng = random.Random(4711)
    values: list[float] = []
    for _ in range(count):
        kind = rng.randrange(6)
        if kind == 0:
            v = rng.randrange(0, 100000) / rng.choice([1, 10, 100, 1000, 10000])
        elif kind == 1:
            v = round(rng.uniform(-1000, 1000), rng.randrange(0, 6))
        elif kind == 2:
            v = (
                rng.randrange(0, 1000) / 1000
                + rng.randrange(0, 10)
                + 0.005 * rng.randrange(0, 3)
            )
        elif kind == 3:
            v = rng.uniform(1e-7, 1e-3) * rng.choice([1, -1])
        elif kind == 4:
            v = float(rng.randrange(1, 10 ** rng.randrange(1, 22)))
        else:
            v = rng.uniform(0, 1) * 10 ** rng.randrange(-10, 25)
        values.append(v)
    probes: list[Probe] = []
    for i, v in enumerate(values):
        lit = repr(v)
        code = (
            f"var x = {lit}; return [String(x), x.toFixed(0), x.toFixed(1), x.toFixed(2), x.toFixed(3), "
            "x.toFixed(5), x.toPrecision(1), x.toPrecision(3), x.toPrecision(7), x.toPrecision(15), "
            "x.toExponential(0), x.toExponential(3), x.toString(16), x.toString(2).length].join('|');"
        )
        probes.append(Probe(f"numgen:{i}", "body", code))
    return probes


def _radix(count: int = 60) -> list[Probe]:
    rng = random.Random(815)
    probes: list[Probe] = []
    for i in range(count):
        kind = rng.randrange(4)
        if kind == 0:
            v = rng.random()
        elif kind == 1:
            v = rng.uniform(1, 1000)
        elif kind == 2:
            v = rng.randrange(1, 100) / rng.choice([3, 7, 10, 100, 1024])
        else:
            v = rng.uniform(1e-6, 1e-2)
        code = (
            f"var x = {v!r}; var r = [3, 5, 6, 7, 9, 11, 12, 20, 36, 8, 32]; var o = []; "
            "for (var i = 0; i < r.length; i++) o.push(x.toString(r[i])); return o.join('|');"
        )
        probes.append(Probe(f"radixgen:{i}", "body", code))
    for j, v in enumerate(("0.1", "1 / 3", "0.7", "123.456", "Math.PI")):
        code = f"var x = {v}; var o = []; for (var r = 2; r <= 36; r++) o.push(x.toString(r)); return o.join('|');"
        probes.append(Probe(f"radixall:{j}", "body", code))
    return probes


def _math(count: int = 200) -> list[Probe]:
    rng = random.Random(1999)
    probes: list[Probe] = []
    for i in range(count):
        a = rng.uniform(-10, 10) * 10 ** rng.randrange(-3, 3)
        b = rng.uniform(0.001, 50)
        c = rng.uniform(-1, 1)
        code = (
            f"var a = {a!r}, b = {b!r}, c = {c!r}; return [Math.sin(a), Math.cos(a), Math.tan(a), Math.exp(a), "
            "Math.log(b), Math.sqrt(b), Math.atan(a), Math.asin(c), Math.acos(c), Math.atan2(a, b), "
            "Math.pow(b, c * 3), Math.pow(a, 3), Math.pow(b, 0.5), Math.exp(c * 50), Math.log(b * 1e-5)].join('|');"
        )
        probes.append(Probe(f"mathgen:{i}", "body", code))
    return probes


def _dates() -> list[Probe]:
    stamps = [
        "Date.UTC(2026, 2, 29, 0, 59, 59)",
        "Date.UTC(2026, 2, 29, 1, 0, 0)",
        "Date.UTC(2026, 9, 25, 0, 59, 59)",
        "Date.UTC(2026, 9, 25, 1, 0, 0)",
        "Date.UTC(1975, 5, 1, 12)",
        "Date.UTC(1980, 3, 6, 12)",
        "Date.UTC(1996, 9, 27, 0, 30)",
        "Date.UTC(1945, 6, 1, 12)",
        "Date.UTC(2040, 6, 1, 12)",
        "Date.UTC(1900, 0, 1)",
        "Date.UTC(1, 0, 1)",
        "Date.UTC(2026, 11, 31, 23, 59, 59, 999)",
        "-1",
        "0",
        "1e12",
    ]
    probes: list[Probe] = []
    for i, s in enumerate(stamps):
        code = (
            f"var d = new Date({s}); return [d.getTimezoneOffset(), d.getFullYear(), d.getMonth(), d.getDate(), "
            "d.getDay(), d.getHours(), d.getMinutes(), d.getSeconds(), d.getMilliseconds(), d.toString(), "
            "d.toLocaleString(), d.toUTCString()].join('|');"
        )
        probes.append(Probe(f"dategen:{i}", "body", code))
    locals_ = [
        (2026, 2, 29, 1, 59),
        (2026, 2, 29, 2, 0),
        (2026, 2, 29, 3, 0),
        (2026, 9, 25, 1, 59),
        (2026, 9, 25, 2, 0),
        (2026, 9, 25, 2, 59),
        (2026, 9, 25, 3, 0),
        (1990, 5, 15, 12, 0),
    ]
    for i, (y, mo, d, h, mi) in enumerate(locals_):
        code = f"var d = new Date({y}, {mo}, {d}, {h}, {mi}); return d.getTime() + '|' + d.getHours() + ':' + d.getMinutes() + '|' + d.getTimezoneOffset();"
        probes.append(Probe(f"datelocal:{i}", "body", code))
    return probes


def probes() -> list[Probe]:
    out = _presence()
    out += [Probe(i, k, c) for i, k, c in _SEMANTIC]
    out += [Probe(f"compile:{i}", "compile", c) for i, c in _COMPILE]
    out += _reserved()
    out += [Probe(i, k, c) for i, k, c in _EXTRA]
    out += _numbers()
    out += _radix()
    out += _math()
    out += _dates()
    out += _case_mapping_full()
    seen: set[str] = set()
    for p in out:
        if p.id in seen:
            raise ValueError(f"duplicate probe id {p.id}")
        seen.add(p.id)
    return out
