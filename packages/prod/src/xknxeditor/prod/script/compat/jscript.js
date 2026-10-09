(function (g) {
  var X = g.__xknx__;
  var host = X.host;
  var ABORT = X.abort;

  var NObject = Object, NFunction = Function, NArray = Array, NString = String, NNumber = Number;
  var NDate = Date, NRegExp = RegExp, NError = Error, NMath = Math, NEval = eval;
  var NTypeError = TypeError, NRangeError = RangeError, NSyntaxError = SyntaxError;
  var NURIError = URIError, NEvalError = EvalError, NReferenceError = ReferenceError;
  var defineProperty = Object.defineProperty;
  var getOwnPropertyNames = Object.getOwnPropertyNames;
  // Captured before the ES3 cleanup below deletes Object.freeze; used to lock the abort hook.
  var nativeFreeze = Object.freeze;
  var setPrototypeOf = Object.setPrototypeOf;
  var getPrototypeOf = Object.getPrototypeOf;
  var isArray = Array.isArray;
  var NWeakMap = WeakMap;
  var OP = Object.prototype, AP = Array.prototype, SP = String.prototype, NP = Number.prototype;
  var DP = Date.prototype, RP = RegExp.prototype, FP = Function.prototype, EP = Error.prototype;
  var fnApply = FP.apply, fnCall = FP.call;
  var objToString = OP.toString, hasOwn = OP.hasOwnProperty;
  var fnToString = FP.toString;
  var aSlice = AP.slice, aPush = AP.push, aJoin = AP.join, aSplice = AP.splice, aUnshift = AP.unshift;
  var sIndexOf = SP.indexOf, sSlice = SP.slice, sSubstr = SP.substr, sSplit = SP.split;
  var sToUpper = SP.toUpperCase, sToLower = SP.toLowerCase, sReplace = SP.replace;
  var rExec = RP.exec, rTest = RP.test, rCompile = RP.compile;
  var rSource = Object.getOwnPropertyDescriptor(RP, "source").get;
  var rFlags = Object.getOwnPropertyDescriptor(RP, "flags").get;
  var rGlobal = Object.getOwnPropertyDescriptor(RP, "global").get;
  var nToString = NP.toString;
  var dGetTime = DP.getTime, dSetTime = DP.setTime;
  var dGetUTCFullYear = DP.getUTCFullYear, dGetUTCMonth = DP.getUTCMonth, dGetUTCDate = DP.getUTCDate;
  var dGetUTCDay = DP.getUTCDay, dGetUTCHours = DP.getUTCHours, dGetUTCMinutes = DP.getUTCMinutes;
  var dGetUTCSeconds = DP.getUTCSeconds, dGetUTCMilliseconds = DP.getUTCMilliseconds;
  var dateUTC = Date.UTC, dateNow = Date.now;
  var nParseInt = parseInt, nParseFloat = parseFloat;
  var nEncodeURI = encodeURI, nEncodeURIComponent = encodeURIComponent;
  var nDecodeURI = decodeURI, nDecodeURIComponent = decodeURIComponent;
  var floor = Math.floor, abs = Math.abs;
  var fromCharCode = String.fromCharCode;

  var natives = new NWeakMap();
  var sources = new NWeakMap();
  var fnmap = {};
  var normalized = new NWeakMap();

  function def(obj, name, fn, nativeName) {
    defineProperty(obj, name, { value: fn, writable: true, configurable: true, enumerable: false });
    if (typeof fn === "function") {
      natives.set(fn, nativeName === undefined ? name : nativeName);
      try { delete fn.name; } catch (ignored) {}
    }
    return fn;
  }

  function isPrim(v) {
    return v === null || (typeof v !== "object" && typeof v !== "function");
  }

  function toInteger(v) {
    var n = NNumber(v);
    if (n !== n) return 0;
    if (n === 0 || n === Infinity || n === -Infinity) return n;
    return n < 0 ? -floor(-n) : floor(n);
  }

  function toObject(v, name) {
    if (v === null || v === undefined) throw jerr(NTypeError, "'this' is null or undefined", -2146823281);
    return NObject(v);
  }

  // ---- errors -------------------------------------------------------------------------------

  function errorObject(Ctor, message, number, name) {
    var e = new NError();
    setPrototypeOf(e, Ctor.prototype);
    delete e.stack;
    delete e.message;
    defineProperty(e, "message", { value: message, writable: true, enumerable: true, configurable: true });
    defineProperty(e, "description", { value: message, writable: true, enumerable: true, configurable: true });
    defineProperty(e, "number", { value: number, writable: true, enumerable: true, configurable: true });
    defineProperty(e, "name", { value: name || Ctor.prototype.name, writable: true, enumerable: true, configurable: true });
    normalized.set(e, true);
    return e;
  }

  function jerr(Ctor, message, number, name) {
    return errorObject(Ctor, message, number, name);
  }

  var ERROR_MAP = [
    [/^(.*) is not defined$/, NTypeError, function (m) { return "'" + m[1] + "' is undefined"; }, -2146823279],
    [/^cannot read property '(.*)' of (?:undefined|null)$/, NTypeError,
      function (m) { return "Unable to get property '" + m[1] + "' of undefined or null reference"; }, -2146823281],
    [/^cannot set property '(.*)' of (?:undefined|null)$/, NTypeError,
      function (m) { return "Unable to set property '" + m[1] + "' of undefined or null reference"; }, -2146823281],
    [/^not a constructor$/, NTypeError, function () { return "Object doesn't support this action"; }, -2146827843],
    [/not a function$/, NTypeError, function () { return "Function expected"; }, -2146823286],
    [/^(?:stack overflow|Maximum call stack size exceeded)$/, NError, function () { return "Out of stack space"; }, -2146828260],
    [/^invalid array length$/, NRangeError, function () { return "Array length must be a finite positive integer"; }, -2146823259],
    [/'in'/, NTypeError, function () { return "Invalid operand to 'in': Object expected"; }, -2146823281],
    [/instanceof/, NTypeError, function () { return "Invalid operand to 'instanceof': Function expected"; }, -2146823286],
    [/^invalid object type$|^not an object$/, NTypeError, function () { return "Object expected"; }, -2146823281]
  ];

  function norm(e) {
    if (e === ABORT || e === null || typeof e !== "object" || normalized.get(e)) return e;
    if (!(e instanceof NError)) return e;
    var message = NString(e.message);
    for (var i = 0; i < ERROR_MAP.length; i++) {
      var m = ERROR_MAP[i][0].exec(message);
      if (m) return errorObject(ERROR_MAP[i][1], ERROR_MAP[i][2](m), ERROR_MAP[i][3]);
    }
    var Ctor = e instanceof NTypeError ? NTypeError : e instanceof NRangeError ? NRangeError :
      e instanceof NSyntaxError ? NSyntaxError : e instanceof NURIError ? NURIError : NError;
    return errorObject(Ctor, message, typeof e.number === "number" ? e.number : -2146827850,
      e instanceof NReferenceError ? "TypeError" : undefined);
  }

  function hostError(message, number) {
    return errorObject(NError, NString(message), number === undefined || number === null ? -2147467259 : number);
  }

  function makeErrorCtor(NCtor) {
    var J = function (a, b) {
      var e = new NError();
      setPrototypeOf(e, J.prototype);
      delete e.stack;
      delete e.message;
      var message = "";
      var number;
      var hasNumber = false;
      if (arguments.length >= 2) {
        number = NNumber(a);
        hasNumber = true;
        message = b === undefined ? "" : toStr(b);
      } else if (arguments.length === 1) {
        if (typeof a === "number" || (typeof a === "string" && /^\s*[-+]?(?:\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?|0[xX][0-9a-fA-F]+)\s*$/.test(a))) {
          number = NNumber(a);
          hasNumber = true;
        } else if (a !== undefined) {
          message = toStr(a);
        }
      } else {
        number = 0;
        hasNumber = true;
      }
      defineProperty(e, "description", { value: message, writable: true, enumerable: true, configurable: true });
      defineProperty(e, "message", { value: message, writable: true, enumerable: true, configurable: true });
      if (hasNumber) defineProperty(e, "number", { value: number, writable: true, enumerable: true, configurable: true });
      defineProperty(e, "name", { value: J.prototype.name, writable: true, enumerable: true, configurable: true });
      normalized.set(e, true);
      return e;
    };
    J.prototype = NCtor.prototype;
    defineProperty(NCtor.prototype, "constructor", { value: J, writable: true, configurable: true, enumerable: false });
    natives.set(J, NCtor.prototype.name);
    try { delete J.name; } catch (ignored) {}
    return J;
  }

  var JError = makeErrorCtor(NError);
  var JTypeError = makeErrorCtor(NTypeError);
  var JRangeError = makeErrorCtor(NRangeError);
  var JSyntaxError = makeErrorCtor(NSyntaxError);
  var JURIError = makeErrorCtor(NURIError);
  var JEvalError = makeErrorCtor(NEvalError);
  var JReferenceError = makeErrorCtor(NReferenceError);
  def(EP, "toString", function () { return "[object Error]"; });

  // ---- numbers and strings ------------------------------------------------------------------

  var numCache = {};
  var numCacheSize = 0;

  function numStr(x) {
    if (x === (x | 0)) return "" + x;
    if (x !== x) return "NaN";
    if (x === Infinity) return "Infinity";
    if (x === -Infinity) return "-Infinity";
    if (floor(x) === x && abs(x) < 1e15) return "" + x;
    var key = "" + x;
    var hit = numCache[key];
    if (hit !== undefined) return hit;
    var s = host("n.str", x);
    if (numCacheSize > 4096) {
      numCache = {};
      numCacheSize = 0;
    }
    numCache[key] = s;
    numCacheSize++;
    return s;
  }

  function toPrim(o, hint) {
    if (isPrim(o)) return o;
    if (hint === undefined) hint = o instanceof NDate ? "string" : "number";
    var order = hint === "string" ? ["toString", "valueOf"] : ["valueOf", "toString"];
    for (var i = 0; i < 2; i++) {
      var f = o[order[i]];
      if (typeof f === "function") {
        var r = fnApply.call(f, o, []);
        if (isPrim(r)) return r;
      }
    }
    throw jerr(NTypeError, "Object doesn't support this property or method", -2146827850);
  }

  function toStr(v) {
    switch (typeof v) {
      case "string": return v;
      case "number": return numStr(v);
      case "boolean": return v ? "true" : "false";
      case "undefined": return "undefined";
    }
    if (v === null) return "null";
    return toStr(toPrim(v, "string"));
  }

  function isIndex(k) {
    return typeof k === "number" ? (k >= 0 && k === floor(k)) : /^(?:0|[1-9][0-9]*)$/.test(k);
  }

  function key(k) {
    if (typeof k === "number" && !(k === floor(k) && abs(k) < 1e15)) return numStr(k);
    return k;
  }

  function keyName(k) {
    return typeof k === "number" ? numStr(k) : NString(k);
  }

  function get(o, k) {
    if (o === null || o === undefined) {
      throw jerr(NTypeError, "Unable to get property '" + keyName(k) + "' of undefined or null reference", -2146823281);
    }
    k = key(k);
    if ((typeof o === "string" || o instanceof NString) && isIndex(k)) return undefined;
    return o[k];
  }

  function mth(o, name) {
    if (o === null || o === undefined) {
      throw jerr(NTypeError, "Unable to get property '" + keyName(name) + "' of undefined or null reference", -2146823281);
    }
    var raw = o.__xk_raw;
    if (raw !== undefined && hasOwn.call(raw, name)) return raw[name];
    return o[name];
  }

  function cget(o, k) {
    var raw = o === null || o === undefined ? undefined : o.__xk_raw;
    if (raw !== undefined && hasOwn.call(raw, k)) return raw[k];
    return get(o, k);
  }

  function callError(f, name) {
    if (f === undefined) return jerr(NTypeError, "Object doesn't support property or method '" + keyName(name) + "'", -2146827850);
    if (f === null) return jerr(NTypeError, "Object expected", -2146823281);
    return jerr(NTypeError, "Function expected", -2146823286);
  }

  function callMember(o, f, name) {
    if (typeof f !== "function") {
      if (o === g && (f === undefined || f === null)) {
        throw jerr(NTypeError, "The value of the property '" + keyName(name) + "' is null or undefined, not a Function object", -2146823281);
      }
      throw callError(f, name);
    }
    return fnApply.call(f, o, fnApply.call(aSlice, arguments, [3]));
  }

  function callFunction(f, name) {
    if (typeof f !== "function") {
      if (name !== null && (f === undefined || f === null)) {
        throw jerr(NTypeError, "The value of the property '" + name + "' is null or undefined, not a Function object", -2146823281);
      }
      throw jerr(NTypeError, "Function expected", -2146823286);
    }
    return fnApply.call(f, undefined, fnApply.call(aSlice, arguments, [2]));
  }

  function add(a, b) {
    var ta = typeof a, tb = typeof b;
    if (ta === "number" && tb === "number") return a + b;
    if (ta === "string" && tb === "string") return a + b;
    try {
      if (!isPrim(a)) a = toPrim(a);
      if (!isPrim(b)) b = toPrim(b);
    } catch (e) {
      if (e === ABORT) throw e;
      return undefined;
    }
    if (typeof a === "string" || typeof b === "string") return toStr(a) + toStr(b);
    return a + b;
  }

  function ctor(f) {
    if (typeof f !== "function") throw jerr(NTypeError, "Object doesn't support this action", -2146827843);
    return f;
  }

  function int64(x) {
    var n = +x;
    return n >= 9223372036854775808 || n <= -9223372036854775808 ? 0 : n;
  }

  function dropNames() {
    for (var i = 0; i < arguments.length; i++) {
      var f = arguments[i];
      if (typeof f === "function") {
        try { delete f.name; } catch (ignored) {}
      }
    }
    return arguments[0];
  }

  function ForIn(o) {
    this.o = o;
    this.visited = {};
    this.queue = [];
    this.k = undefined;
    this.fill();
  }
  ForIn.prototype.fill = function () {
    var o = this.o;
    if (o === null || o === undefined || typeof o === "string" || o instanceof NString) return false;
    var added = false;
    for (var k in o) {
      if (!fnCall.call(hasOwn, this.visited, "$" + k)) {
        var known = false;
        for (var i = 0; i < this.queue.length; i++) {
          if (this.queue[i] === k) {
            known = true;
            break;
          }
        }
        if (!known) {
          aPush.call(this.queue, k);
          added = true;
        }
      }
    }
    return added;
  };
  ForIn.prototype.next = function () {
    while (true) {
      while (this.queue.length) {
        var k = this.queue.shift();
        if (fnCall.call(hasOwn, this.visited, "$" + k)) continue;
        if (!(k in NObject(this.o))) continue;
        this.visited["$" + k] = true;
        this.k = k;
        return true;
      }
      if (!this.fill()) return false;
    }
  };

  function forInIterator(o) {
    return new ForIn(o);
  }

  var ticks = 0;
  var lastYield = dateNow();
  function tick() {
    if (++ticks >= 500) {
      ticks = 0;
      var now = dateNow();
      if (now - lastYield >= 2) {
        lastYield = now;
        X.tick();
      }
    }
  }

  function forInTarget(o) {
    if (typeof o === "string" || o instanceof NString) return {};
    return o;
  }

  function transformSource(code) {
    var r = host("fe.transform", code);
    if (r.error) throw jerr(JSyntaxError, r.error.message, r.error.number);
    for (var k in r.fnmap) if (hasOwn.call(r.fnmap, k)) fnmap[k] = r.fnmap[k];
    return r.code;
  }

  function evalSource(code) {
    return typeof code === "string" ? transformSource(code) : code;
  }

  // ---- String ------------------------------------------------------------------------------

  var JString = function (v) {
    var s = arguments.length ? toStr(v) : "";
    if (new.target) return new NString(s);
    return s;
  };
  JString.prototype = SP;
  def(SP, "constructor", JString);

  var JNumber = function (v) {
    var n = arguments.length ? NNumber(v) : 0;
    if (new.target) return new NNumber(n);
    return n;
  };
  JNumber.prototype = NP;
  def(NP, "constructor", JNumber);
  var NUMBER_CONSTANTS = ["MAX_VALUE", "MIN_VALUE", "NaN", "NEGATIVE_INFINITY", "POSITIVE_INFINITY"];
  for (var nc = 0; nc < NUMBER_CONSTANTS.length; nc++) {
    defineProperty(JNumber, NUMBER_CONSTANTS[nc], { value: NNumber[NUMBER_CONSTANTS[nc]], writable: false, enumerable: false, configurable: false });
  }
  natives.set(JNumber, "Number");
  try { delete JNumber.name; } catch (ignored) {}
  defineProperty(JString, "fromCharCode", { value: NString.fromCharCode, writable: true, configurable: true, enumerable: false });
  natives.set(JString, "String");
  try { delete JString.name; } catch (ignored) {}

  function thisStr(v) {
    if (v === null || v === undefined) throw jerr(NTypeError, "'this' is null or undefined", -2146823281);
    return toStr(v);
  }

  def(SP, "substr", function (start, length) {
    var s = thisStr(this);
    var st = toInteger(start);
    if (st < 0) st = 0;
    var len = length === undefined ? s.length - st : toInteger(length);
    return fnCall.call(sSubstr, s, st, len);
  });

  def(SP, "concat", function () {
    var s = thisStr(this);
    for (var i = 0; i < arguments.length; i++) s += toStr(arguments[i]);
    return s;
  });

  function caseMap(s, upper) {
    if (/^[\x00-\x7f]*$/.test(s)) return fnCall.call(upper ? sToUpper : sToLower, s);
    return host(upper ? "case.upper" : "case.lower", s);
  }
  def(SP, "toUpperCase", function () { return caseMap(thisStr(this), true); });
  def(SP, "toLowerCase", function () { return caseMap(thisStr(this), false); });
  def(SP, "toLocaleUpperCase", function () { return caseMap(thisStr(this), true); });
  def(SP, "toLocaleLowerCase", function () { return caseMap(thisStr(this), false); });
  def(SP, "localeCompare", function (that) { return host("loc.cmp", thisStr(this), toStr(that)); });

  function tag(name, attr) {
    return function (v) {
      var s = thisStr(this);
      return "<" + name + (attr ? " " + attr + "=\"" + toStr(v) + "\"" : "") + ">" + s + "</" + name + ">";
    };
  }
  def(SP, "anchor", tag("A", "NAME"));
  def(SP, "big", tag("BIG"));
  def(SP, "blink", tag("BLINK"));
  def(SP, "bold", tag("B"));
  def(SP, "fixed", tag("TT"));
  def(SP, "fontcolor", tag("FONT", "COLOR"));
  def(SP, "fontsize", tag("FONT", "SIZE"));
  def(SP, "italics", tag("I"));
  def(SP, "link", tag("A", "HREF"));
  def(SP, "small", tag("SMALL"));
  def(SP, "strike", tag("STRIKE"));
  def(SP, "sub", tag("SUB"));
  def(SP, "sup", tag("SUP"));

  // ---- RegExp ------------------------------------------------------------------------------

  function jscriptRegex(p) {
    var out = "";
    var inClass = false;
    for (var i = 0; i < p.length; i++) {
      var c = p.charAt(i);
      if (c === "\\") {
        var n = p.charAt(i + 1);
        if (n === "s") out += inClass ? "\\t\\n\\v\\f\\r " : "[\\t\\n\\v\\f\\r ]";
        else if (n === "S") out += inClass ? "\\0-\\x08\\x0e-\\x1f\\x21-" + fromCharCode(0xffff) : "[^\\t\\n\\v\\f\\r ]";
        else out += c + n;
        i++;
        continue;
      }
      if (inClass) {
        if (c === "]") inClass = false;
        out += c;
        continue;
      }
      if (c === "[") {
        inClass = true;
        out += c;
        if (p.charAt(i + 1) === "^") {
          out += "^";
          i++;
        }
        continue;
      }
      out += c === "." ? "[^\\n]" : c;
    }
    return out;
  }

  function uniqueFlags(flags) {
    var out = "";
    for (var i = 0; i < flags.length; i++) {
      if (out.indexOf(flags.charAt(i)) < 0) out += flags.charAt(i);
    }
    return out;
  }

  function regexError(message, number) {
    return jerr(NError, message, number, "RegExpError");
  }

  function makeRegex(src, flags) {
    if (!/^[gim]*$/.test(flags)) throw regexError("Syntax error in regular expression", -2146823271);
    var r;
    try {
      r = new NRegExp(jscriptRegex(src), uniqueFlags(flags));
    } catch (e) {
      var m = NString(e && e.message);
      if (/unterminated group|expecting '\)'/i.test(m)) throw regexError("Expected ')' in regular expression", -2146823268);
      if (/unterminated character class|expecting '\]'/i.test(m)) throw regexError("Expected ']' in regular expression", -2146823269);
      throw regexError("Syntax error in regular expression", -2146823271);
    }
    sources.set(r, src);
    return r;
  }

  function regexSource(r) {
    var s = sources.get(r);
    return s !== undefined ? s : fnCall.call(rSource, r);
  }

  var JRegExp = function (pattern, flags) {
    if (pattern instanceof NRegExp && flags === undefined) {
      if (!new.target) return pattern;
      var copy = makeRegex(regexSource(pattern), fnCall.call(rFlags, pattern));
      return copy;
    }
    var src = pattern === undefined ? "" : pattern instanceof NRegExp ? regexSource(pattern) : toStr(pattern);
    return makeRegex(src, flags === undefined ? "" : toStr(flags));
  };
  JRegExp.prototype = RP;
  def(RP, "constructor", JRegExp);
  natives.set(JRegExp, "RegExp");
  try { delete JRegExp.name; } catch (ignored) {}

  var STATIC_NAMES = ["$1", "$2", "$3", "$4", "$5", "$6", "$7", "$8", "$9"];
  function setStatic(name, value) {
    defineProperty(JRegExp, name, { value: value, writable: true, enumerable: false, configurable: true });
  }
  function resetStatics() {
    for (var i = 0; i < STATIC_NAMES.length; i++) setStatic(STATIC_NAMES[i], "");
    setStatic("input", "");
    setStatic("$_", "");
    setStatic("lastMatch", "");
    setStatic("$&", "");
    setStatic("lastParen", "");
    setStatic("$+", "");
    setStatic("leftContext", "");
    setStatic("$`", "");
    setStatic("rightContext", "");
    setStatic("$'", "");
    setStatic("index", -1);
    setStatic("lastIndex", -1);
  }
  resetStatics();
  defineProperty(JRegExp, "input", {
    get: function () { return JRegExp.$_; },
    set: function (v) { setStatic("$_", toStr(v)); },
    enumerable: false, configurable: true
  });

  function updateStatics(m, s) {
    for (var i = 0; i < STATIC_NAMES.length; i++) setStatic(STATIC_NAMES[i], i + 1 < m.length ? m[i + 1] : "");
    setStatic("$_", s);
    setStatic("lastMatch", m[0]);
    setStatic("$&", m[0]);
    var lp = m.length > 1 ? m[m.length - 1] : "";
    setStatic("lastParen", lp);
    setStatic("$+", lp);
    var left = fnCall.call(sSlice, s, 0, m.index);
    var right = fnCall.call(sSlice, s, m.index + m[0].length);
    setStatic("leftContext", left);
    setStatic("$`", left);
    setStatic("rightContext", right);
    setStatic("$'", right);
    setStatic("index", m.index);
    setStatic("lastIndex", m.index + m[0].length);
  }

  function jexec(re, s) {
    var m = fnCall.call(rExec, re, s);
    if (m === null) return null;
    for (var i = 1; i < m.length; i++) if (m[i] === undefined) m[i] = "";
    if (fnCall.call(rGlobal, re) && m[0].length === 0 && re.lastIndex === m.index) re.lastIndex = m.index + 1;
    updateStatics(m, s);
    return m;
  }

  def(RP, "exec", function (s) { return jexec(this, toStr(s)); });
  def(RP, "test", function (s) { return jexec(this, toStr(s)) !== null; });
  def(RP, "compile", function (pattern, flags) {
    var src = pattern === undefined ? "" : pattern instanceof NRegExp ? regexSource(pattern) : toStr(pattern);
    var fl = flags === undefined ? "" : toStr(flags);
    if (!/^[gim]*$/.test(fl)) throw regexError("Syntax error in regular expression", -2146823271);
    fnCall.call(rCompile, this, jscriptRegex(src), uniqueFlags(fl));
    sources.set(this, src);
    return this;
  });
  function regexToString(r) {
    var f = fnCall.call(rFlags, r);
    var out = "/" + regexSource(r) + "/";
    if (f.indexOf("i") >= 0) out += "i";
    if (f.indexOf("g") >= 0) out += "g";
    if (f.indexOf("m") >= 0) out += "m";
    return out;
  }
  def(RP, "toString", function () { return regexToString(this); });
  defineProperty(RP, "source", { get: function () { return regexSource(this); }, enumerable: false, configurable: true });
  defineProperty(RP, "lastIndex", { value: 0, writable: true, enumerable: false, configurable: true });
  var FLAG_GETTERS = ["global", "ignoreCase", "multiline"];
  for (var fg = 0; fg < FLAG_GETTERS.length; fg++) {
    (function (name) {
      var nativeGet = Object.getOwnPropertyDescriptor(RP, name).get;
      defineProperty(RP, name, {
        get: function () {
          "use strict";
          return this === RP ? false : fnCall.call(nativeGet, this);
        },
        enumerable: false, configurable: true
      });
    })(FLAG_GETTERS[fg]);
  }

  function literalRegex(r, src, flags) {
    sources.set(r, src);
    return r;
  }

  function toRegex(v) {
    return v instanceof NRegExp ? v : makeRegex(v === undefined ? "" : toStr(v), "");
  }

  def(SP, "match", function (re) {
    var s = thisStr(this);
    var r = toRegex(re);
    if (!fnCall.call(rGlobal, r)) return jexec(r, s);
    r.lastIndex = 0;
    var out = [];
    var m;
    while ((m = jexec(r, s)) !== null) aPush.call(out, m[0]);
    return out.length ? out : null;
  });

  def(SP, "search", function (re) {
    var s = thisStr(this);
    var r = toRegex(re);
    var saved = r.lastIndex;
    r.lastIndex = 0;
    var m = jexec(r, s);
    r.lastIndex = saved;
    return m === null ? -1 : m.index;
  });

  function expand(repl, m, s, groups) {
    var out = "";
    for (var i = 0; i < repl.length; i++) {
      var c = repl.charAt(i);
      if (c !== "$" || i + 1 >= repl.length) {
        out += c;
        continue;
      }
      var n = repl.charAt(i + 1);
      if (n === "$") { out += "$"; i++; continue; }
      if (n === "&") { out += m[0]; i++; continue; }
      if (n === "`") { out += fnCall.call(sSlice, s, 0, m.index); i++; continue; }
      if (n === "'") { out += fnCall.call(sSlice, s, m.index + m[0].length); i++; continue; }
      if (n >= "0" && n <= "9") {
        var two = repl.charAt(i + 2);
        if (two >= "0" && two <= "9") {
          var idx2 = nParseInt(n + two, 10);
          if (idx2 >= 1 && idx2 <= groups) { out += m[idx2]; i += 2; continue; }
        }
        var idx = nParseInt(n, 10);
        if (idx >= 1 && idx <= groups) { out += m[idx]; i++; continue; }
      }
      out += c;
    }
    return out;
  }

  function regexReplace(s, r, repl) {
    var global = fnCall.call(rGlobal, r);
    var lastEnd = 0;
    var isFn = typeof repl === "function";
    var replStr = isFn ? null : toStr(repl);
    var out = "";
    var pos = 0;
    if (global) r.lastIndex = 0;
    while (true) {
      var saved = r.lastIndex;
      var m = jexec(r, s);
      if (m === null) break;
      out += fnCall.call(sSlice, s, pos, m.index);
      if (isFn) {
        var args = [];
        for (var i = 0; i < m.length; i++) aPush.call(args, m[i]);
        aPush.call(args, m.index, s);
        out += toStr(fnApply.call(repl, undefined, args));
      } else {
        out += expand(replStr, m, s, m.length - 1);
      }
      pos = m.index + m[0].length;
      lastEnd = pos;
      if (!global) break;
      if (r.lastIndex <= saved && m[0].length === 0) r.lastIndex = saved + 1;
    }
    if (global) r.lastIndex = lastEnd;
    return out + fnCall.call(sSlice, s, pos);
  }

  def(SP, "replace", function (pattern, repl) {
    var s = thisStr(this);
    if (pattern instanceof NRegExp) return regexReplace(s, pattern, repl);
    var p = toStr(pattern);
    var idx = fnCall.call(sIndexOf, s, p);
    if (idx < 0) return s;
    var rep = typeof repl === "function" ? toStr(repl(p, idx, s)) : toStr(repl);
    return fnCall.call(sSlice, s, 0, idx) + rep + fnCall.call(sSlice, s, idx + p.length);
  });

  def(SP, "split", function (sep, limit) {
    var s = thisStr(this);
    var lim = limit === undefined ? 4294967295 : (NNumber(limit) >>> 0);
    var out = [];
    if (lim === 0) return out;
    if (sep === undefined) return [s];
    if (!(sep instanceof NRegExp)) {
      var parts = fnCall.call(sSplit, s, toStr(sep));
      return parts.length > lim ? fnCall.call(aSlice, parts, 0, lim) : parts;
    }
    var src = regexSource(sep);
    var flags = fnCall.call(rFlags, sep);
    var re = new NRegExp(jscriptRegex(src), uniqueFlags(flags.replace("g", "") + "g"));
    var p = 0;
    var q = 0;
    var len = s.length;
    while (q <= len) {
      re.lastIndex = q;
      var m = fnCall.call(rExec, re, s);
      if (m === null) break;
      var mi = m.index;
      var ml = m[0].length;
      var piece;
      if (ml === 0) {
        if (mi >= len) break;
        piece = fnCall.call(sSlice, s, p, mi + 1);
        p = mi + 1;
        q = mi + 1;
      } else {
        piece = fnCall.call(sSlice, s, p, mi);
        p = mi + ml;
        q = mi + ml;
      }
      if (piece.length) {
        aPush.call(out, piece);
        if (out.length >= lim) return out;
      }
    }
    var rest = fnCall.call(sSlice, s, p);
    if (rest.length && out.length < lim) aPush.call(out, rest);
    return out;
  });

  // ---- Array -------------------------------------------------------------------------------

  def(AP, "join", function (sep) {
    var o = toObject(this);
    var len = o.length >>> 0;
    var sp = arguments.length === 0 ? "," : toStr(sep);
    var out = "";
    for (var i = 0; i < len; i++) {
      if (i) out += sp;
      var v = o[i];
      if (v !== undefined && v !== null) out += toStr(v);
    }
    return out;
  });
  var jJoin = AP.join;
  def(AP, "toString", function () { return fnCall.call(jJoin, this); });
  def(AP, "toLocaleString", function () {
    var o = toObject(this);
    var len = o.length >>> 0;
    var sep = host("loc.list") + " ";
    var out = "";
    for (var i = 0; i < len; i++) {
      if (i) out += sep;
      var v = o[i];
      if (v !== undefined && v !== null) {
        var f = NObject(v).toLocaleString;
        out += toStr(typeof f === "function" ? fnCall.call(f, v) : v);
      }
    }
    return out;
  });
  def(AP, "unshift", function () {
    fnApply.call(aUnshift, this, arguments);
    return undefined;
  });
  def(AP, "splice", function (start, count) {
    if (arguments.length === 0) return [];
    if (arguments.length === 1) return fnCall.call(aSplice, this, start, 0);
    return fnApply.call(aSplice, this, arguments);
  });
  def(AP, "sort", function (cmp) {
    if (arguments.length > 0 && typeof cmp !== "function") {
      throw jerr(NTypeError, "Array.prototype.sort: argument is not a JavaScript object", -2146823274);
    }
    var o = toObject(this);
    var len = o.length >>> 0;
    var vals = [];
    var undef = 0;
    var holes = 0;
    for (var i = 0; i < len; i++) {
      if (i in o) {
        var v = o[i];
        if (v === undefined) undef++;
        else aPush.call(vals, v);
      } else {
        holes++;
      }
    }
    function compare(x, y) {
      if (cmp === undefined) {
        var a = toStr(x), b = toStr(y);
        return a < b ? -1 : a > b ? 1 : 0;
      }
      return NNumber(fnCall.call(cmp, undefined, x, y));
    }
    for (var k = 1; k < vals.length; k++) {
      var x = vals[k];
      if (compare(x, vals[k - 1]) >= 0) continue;
      var lo = 0;
      var hi = k - 1;
      while (lo <= hi) {
        var mid = (lo + hi) >> 1;
        if (compare(x, vals[mid]) < 0) hi = mid - 1;
        else lo = mid + 1;
      }
      for (var j = k; j > lo; j--) vals[j] = vals[j - 1];
      vals[lo] = x;
    }
    var n = 0;
    for (; n < vals.length; n++) o[n] = vals[n];
    for (var u = 0; u < undef; u++) o[n++] = undefined;
    for (var h = 0; h < holes; h++) delete o[n++];
    return o;
  });

  // ---- Number ------------------------------------------------------------------------------

  function thisNumber(v, name) {
    if (typeof v === "number") return v;
    if (v instanceof NNumber) return fnCall.call(NP.valueOf, v);
    throw jerr(NTypeError, name + ": 'this' is not a Number object", -2146823287);
  }

  def(NP, "toString", function (radix) {
    var x = thisNumber(this, "Number.prototype.toString");
    if (arguments.length === 0) return numStr(x);
    if (radix === undefined) throw jerr(NTypeError, "Invalid procedure call or argument", -2146828283);
    var r = toInteger(radix);
    if (r < 2 || r > 36) throw jerr(NTypeError, "Invalid procedure call or argument", -2146828283);
    if (r === 10) return numStr(x);
    if (x === (x | 0)) return fnCall.call(nToString, x, r);
    return host("n.radix", x, r);
  });
  def(NP, "toLocaleString", function () {
    return host("loc.num", thisNumber(this, "Number.prototype.toLocaleString"));
  });
  function special(x) {
    if (x !== x) return "NaN";
    if (x === Infinity) return "Infinity";
    if (x === -Infinity) return "-Infinity";
    return null;
  }
  def(NP, "toFixed", function (digits) {
    var x = thisNumber(this, "Number.prototype.toFixed");
    var d = toInteger(digits);
    if (d < 0 || d > 20) throw jerr(NRangeError, "The number of fractional digits is out of range", -2146823262);
    return special(x) || host("n.fixed", x, d);
  });
  def(NP, "toExponential", function (digits) {
    var x = thisNumber(this, "Number.prototype.toExponential");
    var d = digits === undefined ? -1 : toInteger(digits);
    if (digits !== undefined && (d < 0 || d > 20)) {
      throw jerr(NRangeError, "The number of fractional digits is out of range", -2146823262);
    }
    return special(x) || host("n.exp", x, d);
  });
  def(NP, "toPrecision", function (precision) {
    var x = thisNumber(this, "Number.prototype.toPrecision");
    if (arguments.length === 0) return numStr(x);
    var p = precision === undefined ? 0 : toInteger(precision);
    if (p < 1 || p > 21) throw jerr(NRangeError, "The precision is out of range", -2146823261);
    return special(x) || host("n.prec", x, p);
  });

  def(g, "parseInt", function (s, radix) {
    var str = toStr(s);
    var r = radix === undefined ? 0 : (NNumber(radix) | 0);
    if (r === 0) {
      var t = fnCall.call(sReplace, str, /^\s+/, "");
      var sign = "";
      var c = t.charAt(0);
      if (c === "-" || c === "+") {
        sign = c;
        t = fnCall.call(sSlice, t, 1);
      }
      if (t.length > 1 && t.charAt(0) === "0" && t.charAt(1) !== "x" && t.charAt(1) !== "X") {
        return nParseInt(sign + t, 8);
      }
    }
    return nParseInt(str, r);
  });
  def(g, "parseFloat", function (s) { return nParseFloat(toStr(s)); });
  def(NMath, "round", function (x) { return floor(NNumber(x) + 0.5); });
  function finite(n) {
    return n === n && n !== Infinity && n !== -Infinity && n !== 0;
  }
  var MATH1 = ["sin", "cos", "tan", "atan", "asin", "acos", "log", "exp"];
  for (var mi = 0; mi < MATH1.length; mi++) {
    (function (name) {
      var nativeFn = NMath[name];
      def(NMath, name, function (x) {
        var n = NNumber(x);
        return finite(n) ? host("m." + name, n) : nativeFn(n);
      });
    })(MATH1[mi]);
  }
  var nAtan2 = NMath.atan2, nPow = NMath.pow;
  def(NMath, "atan2", function (y, x) {
    var a = NNumber(y), b = NNumber(x);
    return finite(a) && finite(b) ? host("m.atan2", a, b) : nAtan2(a, b);
  });
  def(NMath, "pow", function (x, y) {
    var a = NNumber(x), b = NNumber(y);
    return finite(a) && finite(b) ? host("m.pow", a, b) : nPow(a, b);
  });

  function uriError(fn, decode) {
    return function (s) {
      try {
        return fn(toStr(s));
      } catch (e) {
        if (decode) throw jerr(NURIError, "The URI to be decoded is not a valid encoding", -2146823263);
        throw jerr(NURIError, "The URI to be encoded contains an invalid character", -2146823264);
      }
    };
  }
  def(g, "encodeURI", uriError(nEncodeURI, false));
  def(g, "encodeURIComponent", uriError(nEncodeURIComponent, false));
  def(g, "decodeURI", uriError(nDecodeURI, true));
  def(g, "decodeURIComponent", uriError(nDecodeURIComponent, true));

  // ---- Object and Function ------------------------------------------------------------------

  def(OP, "toString", function () {
    "use strict";
    if (this === undefined || this === null) return "[object Object]";
    var t = fnCall.call(objToString, this);
    return t === "[object Arguments]" ? "[object Object]" : t;
  });
  def(OP, "hasOwnProperty", function (k) {
    var name = key(k);
    if ((typeof this === "string" || this instanceof NString) && isIndex(name)) return false;
    return fnCall.call(hasOwn, this, name);
  });

  def(FP, "toString", function () {
    if (typeof this !== "function") throw jerr(NTypeError, "Function expected", -2146823286);
    var nativeName = natives.get(this);
    if (nativeName !== undefined) return "\nfunction " + nativeName + "() {\n    [native code]\n}\n";
    var s = fnCall.call(fnToString, this);
    var orig = fnmap[s];
    if (orig !== undefined) return orig;
    var m = /^function ([\w$]*)\(\) \{\n    \[native code\]\n\}$/.exec(s);
    if (m) return "\nfunction " + m[1] + "() {\n    [native code]\n}\n";
    return s;
  });

  def(FP, "apply", function (thisArg, args) {
    if (arguments.length < 2) return fnCall.call(fnApply, this, thisArg, []);
    if (args === null || args === undefined) {
      throw jerr(NTypeError, "Function.prototype.apply: argument is null or undefined", -2146823281);
    }
    if (!isArray(args) && fnCall.call(objToString, args) !== "[object Arguments]") {
      throw jerr(NTypeError, "Function.prototype.apply: Array or arguments object expected", -2146823260);
    }
    return fnCall.call(fnApply, this, thisArg, args);
  });

  var JFunction = function () {
    var n = arguments.length;
    var params = [];
    for (var i = 0; i < n - 1; i++) aPush.call(params, toStr(arguments[i]));
    var body = n ? toStr(arguments[n - 1]) : "";
    var src = "function anonymous(" + fnCall.call(aJoin, params, ", ") + ") {\n" + body + "\n}";
    var f = (0, NEval)(transformSource("(" + src + ")"));
    fnmap[fnCall.call(fnToString, f)] = src;
    return f;
  };
  JFunction.prototype = FP;
  def(FP, "constructor", JFunction);
  natives.set(JFunction, "Function");
  try { delete JFunction.name; } catch (ignored) {}

  // ---- Date --------------------------------------------------------------------------------

  var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var MS_DAY = 86400000;
  var tz = host("tz.rule");

  function dayFromYear(y) {
    return 365 * (y - 1970) + floor((y - 1969) / 4) - floor((y - 1901) / 100) + floor((y - 1601) / 400);
  }

  function nthWeekday(y, month, week, weekday) {
    var first = dateUTC(y, month, 1);
    var firstDay = new NDate(first);
    var wd = fnCall.call(dGetUTCDay, firstDay);
    var day = 1 + ((weekday - wd + 7) % 7) + (week - 1) * 7;
    if (week === 5) {
      var dim = (dateUTC(y, month + 1, 1) - first) / MS_DAY;
      while (day > dim) day -= 7;
    }
    return dateUTC(y, month, day);
  }

  function dst(t) {
    if (!tz.dst || t !== t) return 0;
    var d = new NDate(t + tz.std * 60000);
    var y = fnCall.call(dGetUTCFullYear, d);
    var r = tz.dst;
    var start = nthWeekday(y, r.start[0], r.start[1], r.start[2]) + r.start[3] * 60000 - tz.std * 60000;
    var end = nthWeekday(y, r.end[0], r.end[1], r.end[2]) + r.end[3] * 60000 - (tz.std + r.delta) * 60000;
    var inside = start < end ? (t >= start && t < end) : (t >= start || t < end);
    return inside ? r.delta * 60000 : 0;
  }

  function localTime(t) {
    return t + tz.std * 60000 + dst(t);
  }

  function utcTime(t) {
    var u = t - tz.std * 60000;
    return u - dst(u);
  }

  function timeClip(t) {
    if (t !== t || abs(t) > 8.64e15) return NaN;
    return t < 0 ? -floor(-t) : floor(t);
  }

  function makeTime(y, mo, d, h, mi, s, ms) {
    var vals = [y, mo, d, h, mi, s, ms];
    for (var i = 0; i < vals.length; i++) {
      var v = NNumber(vals[i]);
      if (v !== v || v === Infinity || v === -Infinity) return NaN;
      vals[i] = toInteger(v);
    }
    var yy = vals[0];
    var t = dateUTC(2000, 0, 1);
    var nd = new NDate(0);
    fnCall.call(DP.setUTCFullYear, nd, yy, vals[1], vals[2]);
    fnCall.call(DP.setUTCHours, nd, vals[3], vals[4], vals[5], vals[6]);
    t = fnCall.call(dGetTime, nd);
    return t;
  }

  function fields(t) {
    var d = new NDate(t);
    return {
      y: fnCall.call(dGetUTCFullYear, d), mo: fnCall.call(dGetUTCMonth, d), d: fnCall.call(dGetUTCDate, d),
      wd: fnCall.call(dGetUTCDay, d), h: fnCall.call(dGetUTCHours, d), mi: fnCall.call(dGetUTCMinutes, d),
      s: fnCall.call(dGetUTCSeconds, d), ms: fnCall.call(dGetUTCMilliseconds, d)
    };
  }

  function thisTime(v, name) {
    if (!(v instanceof NDate)) throw jerr(NTypeError, "Date.prototype." + name + ": 'this' is not a Date object", -2146823282);
    return fnCall.call(dGetTime, v);
  }

  function pad2(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  function yearText(y) {
    return y > 0 ? "" + y : (1 - y) + " B.C.";
  }

  function offsetText(t) {
    var off = (localTime(t) - t) / 60000;
    var sign = off < 0 ? "-" : "+";
    off = abs(off);
    return "UTC" + sign + pad2(floor(off / 60)) + pad2(off % 60);
  }

  function dateText(t, part) {
    if (t !== t) return "NaN";
    var f = fields(localTime(t));
    var date = DAYS[f.wd] + " " + MONTHS[f.mo] + " " + f.d;
    var time = pad2(f.h) + ":" + pad2(f.mi) + ":" + pad2(f.s) + " " + offsetText(t);
    if (part === "date") return date + " " + yearText(f.y);
    if (part === "time") return time;
    return date + " " + time + " " + yearText(f.y);
  }

  function utcText(t) {
    if (t !== t) return "NaN";
    var f = fields(t);
    return DAYS[f.wd] + ", " + f.d + " " + MONTHS[f.mo] + " " + yearText(f.y) + " " + pad2(f.h) + ":" +
      pad2(f.mi) + ":" + pad2(f.s) + " UTC";
  }

  function localeText(t, part) {
    if (t !== t) return "NaN";
    var f = fields(localTime(t));
    return host("loc.date", [f.y, f.mo, f.d, f.wd, f.h, f.mi, f.s], part);
  }

  function parseDate(s) {
    var r = host("date.parse", toStr(s));
    if (r === null) return NaN;
    var t = makeTime(r[0], r[1], r[2], r[3], r[4], r[5], 0);
    if (r[6] === null) return timeClip(utcTime(t));
    return timeClip(t - r[6] * 60000);
  }

  var JDate = function (a, b, c, d, e, f, h) {
    if (!new.target) return dateText(dateNow(), "full");
    var n = arguments.length;
    var t;
    if (n === 0) {
      t = dateNow();
    } else if (n === 1) {
      var v = isPrim(a) ? a : toPrim(a);
      t = typeof v === "string" ? parseDate(v) : timeClip(NNumber(v));
    } else {
      var y = NNumber(a);
      if (y === y) {
        var yi = toInteger(y);
        if (yi >= 0 && yi <= 99) y = 1900 + yi;
      }
      t = timeClip(utcTime(makeTime(y, b, n > 2 ? c : 1, n > 3 ? d : 0, n > 4 ? e : 0, n > 5 ? f : 0, n > 6 ? h : 0)));
    }
    return new NDate(t);
  };
  JDate.prototype = DP;
  def(DP, "constructor", JDate);
  natives.set(JDate, "Date");
  try { delete JDate.name; } catch (ignored) {}
  defineProperty(JDate, "parse", { value: def({}, "parse", function (s) { return parseDate(s); }), writable: true, configurable: true, enumerable: false });
  defineProperty(JDate, "UTC", { value: Date.UTC, writable: true, configurable: true, enumerable: false });
  defineProperty(JDate, "now", { value: Date.now, writable: true, configurable: true, enumerable: false });

  function localGetter(name, field) {
    def(DP, name, function () {
      var t = thisTime(this, name);
      if (t !== t) return NaN;
      return fields(localTime(t))[field];
    });
  }
  localGetter("getFullYear", "y");
  localGetter("getMonth", "mo");
  localGetter("getDate", "d");
  localGetter("getDay", "wd");
  localGetter("getHours", "h");
  localGetter("getMinutes", "mi");
  localGetter("getSeconds", "s");
  localGetter("getMilliseconds", "ms");
  def(DP, "getTimezoneOffset", function () {
    var t = thisTime(this, "getTimezoneOffset");
    if (t !== t) return NaN;
    return (t - localTime(t)) / 60000;
  });
  def(DP, "getYear", function () {
    var t = thisTime(this, "getYear");
    if (t !== t) return NaN;
    var y = fields(localTime(t)).y;
    return y >= 1900 && y <= 1999 ? y - 1900 : y;
  });

  function localSetter(name, build) {
    def(DP, name, function () {
      var t = thisTime(this, name);
      var f = fields(localTime(t));
      var lt = build(f, arguments, t !== t);
      var u = timeClip(utcTime(lt));
      fnCall.call(dSetTime, this, u);
      return u;
    });
  }
  function arg(args, i, dflt) {
    return i < args.length ? args[i] : dflt;
  }
  localSetter("setMilliseconds", function (f, a, nan) {
    return nan ? NaN : makeTime(f.y, f.mo, f.d, f.h, f.mi, f.s, a[0]);
  });
  localSetter("setSeconds", function (f, a, nan) {
    return nan ? NaN : makeTime(f.y, f.mo, f.d, f.h, f.mi, a[0], arg(a, 1, f.ms));
  });
  localSetter("setMinutes", function (f, a, nan) {
    return nan ? NaN : makeTime(f.y, f.mo, f.d, f.h, a[0], arg(a, 1, f.s), arg(a, 2, f.ms));
  });
  localSetter("setHours", function (f, a, nan) {
    return nan ? NaN : makeTime(f.y, f.mo, f.d, a[0], arg(a, 1, f.mi), arg(a, 2, f.s), arg(a, 3, f.ms));
  });
  localSetter("setDate", function (f, a, nan) {
    return nan ? NaN : makeTime(f.y, f.mo, a[0], f.h, f.mi, f.s, f.ms);
  });
  localSetter("setMonth", function (f, a, nan) {
    return nan ? NaN : makeTime(f.y, a[0], arg(a, 1, f.d), f.h, f.mi, f.s, f.ms);
  });
  localSetter("setFullYear", function (f, a, nan) {
    if (nan) return makeTime(a[0], arg(a, 1, 0), arg(a, 2, 1), 0, 0, 0, 0);
    return makeTime(a[0], arg(a, 1, f.mo), arg(a, 2, f.d), f.h, f.mi, f.s, f.ms);
  });
  localSetter("setYear", function (f, a, nan) {
    var y = NNumber(a[0]);
    if (y === y) {
      var yi = toInteger(y);
      if (yi >= 0 && yi <= 99) y = 1900 + yi;
    }
    if (nan) return makeTime(y, 0, 1, 0, 0, 0, 0);
    return makeTime(y, f.mo, f.d, f.h, f.mi, f.s, f.ms);
  });

  def(DP, "toString", function () { return dateText(thisTime(this, "toString"), "full"); });
  def(DP, "toDateString", function () { return dateText(thisTime(this, "toDateString"), "date"); });
  def(DP, "toTimeString", function () { return dateText(thisTime(this, "toTimeString"), "time"); });
  def(DP, "toUTCString", function () { return utcText(thisTime(this, "toUTCString")); });
  def(DP, "toGMTString", function () { return utcText(thisTime(this, "toGMTString")); });
  def(DP, "toLocaleString", function () { return localeText(thisTime(this, "toLocaleString"), "full"); });
  def(DP, "toLocaleDateString", function () { return localeText(thisTime(this, "toLocaleDateString"), "date"); });
  def(DP, "toLocaleTimeString", function () { return localeText(thisTime(this, "toLocaleTimeString"), "time"); });
  def(DP, "getVarDate", function () { return new NDate(thisTime(this, "getVarDate")); });
  var DATE_NATIVE = ["getTime", "valueOf", "setTime", "getUTCFullYear", "getUTCMonth", "getUTCDate", "getUTCDay",
    "getUTCHours", "getUTCMinutes", "getUTCSeconds", "getUTCMilliseconds", "setUTCFullYear", "setUTCMonth",
    "setUTCDate", "setUTCHours", "setUTCMinutes", "setUTCSeconds", "setUTCMilliseconds"];
  for (var dn = 0; dn < DATE_NATIVE.length; dn++) {
    (function (name) {
      var nativeFn = DP[name];
      def(DP, name, function () {
        thisTime(this, name);
        return fnApply.call(nativeFn, this, arguments);
      });
    })(DATE_NATIVE[dn]);
  }

  // ---- JScript-only globals ------------------------------------------------------------------

  var enumState = new NWeakMap();
  var JEnumerator = function (c) {
    var items;
    if (c === undefined) items = [];
    else if (isArray(c)) items = fnCall.call(aSlice, c);
    else throw jerr(NTypeError, "Object not a collection", -2146827837);
    var self = new.target ? this : setPrototypeOf({}, JEnumerator.prototype);
    enumState.set(self, { items: items, i: 0 });
    return self;
  };
  def(JEnumerator.prototype, "atEnd", function () { var s = enumState.get(this); return s.i >= s.items.length; });
  def(JEnumerator.prototype, "item", function () { var s = enumState.get(this); return s.i < s.items.length ? s.items[s.i] : undefined; });
  def(JEnumerator.prototype, "moveFirst", function () { enumState.get(this).i = 0; });
  def(JEnumerator.prototype, "moveNext", function () { var s = enumState.get(this); if (s.i < s.items.length) s.i++; });

  var debugObject = {};
  def(debugObject, "write", function () {});
  def(debugObject, "writeln", function () {});
  defineProperty(debugObject, "setNonUserCodeExceptions", { value: undefined, writable: true, enumerable: true, configurable: true });
  defineProperty(debugObject, "debuggerEnabled", { value: false, writable: true, enumerable: true, configurable: true });

  var GLOBALS = {
    String: JString,
    Number: JNumber,
    RegExp: JRegExp,
    Date: JDate,
    Function: JFunction,
    Error: JError,
    TypeError: JTypeError,
    RangeError: JRangeError,
    SyntaxError: JSyntaxError,
    URIError: JURIError,
    EvalError: JEvalError,
    ReferenceError: JReferenceError,
    Enumerator: JEnumerator,
    Debug: debugObject
  };
  for (var gname in GLOBALS) {
    defineProperty(g, gname, { value: GLOBALS[gname], writable: true, configurable: true, enumerable: false });
  }
  natives.set(JEnumerator, "Enumerator");
  defineProperty(FP, "arguments", {
    get: function () {
      var s = this.__xk_as;
      return s && s.length ? s[s.length - 1] : null;
    },
    set: function () {},
    enumerable: false,
    configurable: true
  });

  function argsEnter(args) {
    var f = args.callee;
    if (!hasOwn.call(f, "__xk_as")) defineProperty(f, "__xk_as", { value: [] });
    f.__xk_as.push(args);
    return f;
  }

  function argsExit(f) {
    f.__xk_as.pop();
  }

  function typeOf(v) {
    if (typeof v === "function" && v.__xk_unknown === true) return "unknown";
    return typeof v;
  }
  defineProperty(FP, "caller", { value: null, writable: true, enumerable: false, configurable: true });
  var JSCRIPT_VALUES = { __xk_undefined: undefined, __xk_NaN: NaN, __xk_Infinity: Infinity };
  for (var jv in JSCRIPT_VALUES) {
    defineProperty(g, jv, { value: JSCRIPT_VALUES[jv], writable: true, enumerable: false, configurable: false });
  }
  def(g, "VBArray", function () { throw jerr(NTypeError, "VBArray: argument is not a VBArray object", -2146823275); });
  def(g, "ActiveXObject", function () { throw jerr(NError, "Automation server can't create object", -2146827859); });
  def(g, "GetObject", function () { throw jerr(NError, "", -2147221020); });
  def(g, "CollectGarbage", function () { return undefined; });
  def(g, "ScriptEngine", function () { return "JScript"; });
  def(g, "ScriptEngineMajorVersion", function () { return 11; });
  def(g, "ScriptEngineMinorVersion", function () { return 0; });
  def(g, "ScriptEngineBuildVersion", function () { return 16384; });

  // ---- remove what JScript does not have -----------------------------------------------------

  var REMOVE = {
    "": "AggregateError ArrayBuffer Atomics BigInt BigInt64Array BigUint64Array DOMException DataView FinalizationRegistry Float16Array Float32Array Float64Array Int16Array Int32Array Int8Array InternalError Iterator JSON Map Promise Proxy Reflect Set SharedArrayBuffer Symbol Uint16Array Uint32Array Uint8Array Uint8ClampedArray WeakMap WeakRef WeakSet console globalThis performance queueMicrotask",
    Array: "from fromAsync isArray of",
    "Array.prototype": "at copyWithin entries every fill filter find findIndex findLast findLastIndex flat flatMap forEach includes indexOf keys lastIndexOf map reduce reduceRight some toReversed toSorted toSpliced values with",
    "Date.prototype": "toISOString toJSON",
    Error: "captureStackTrace isError prepareStackTrace stackTraceLimit",
    "Function.prototype": "bind columnNumber fileName lineNumber name",
    Math: "acosh asinh atanh cbrt clz32 cosh expm1 f16round fround hypot imul log10 log1p log2 sign sinh sumPrecise tanh trunc",
    Number: "EPSILON MAX_SAFE_INTEGER MIN_SAFE_INTEGER isFinite isInteger isNaN isSafeInteger parseFloat parseInt",
    Object: "assign create defineProperties defineProperty entries freeze fromEntries getOwnPropertyDescriptor getOwnPropertyDescriptors getOwnPropertyNames getOwnPropertySymbols getPrototypeOf groupBy hasOwn is isExtensible isFrozen isSealed keys preventExtensions seal setPrototypeOf values",
    global: "",
    "Object.prototype": "__defineGetter__ __defineSetter__ __lookupGetter__ __lookupSetter__ __proto__",
    RegExp: "escape",
    "RegExp.prototype": "dotAll flags hasIndices sticky unicode unicodeSets",
    String: "fromCodePoint raw",
    "String.prototype": "at codePointAt endsWith includes isWellFormed matchAll normalize padEnd padStart repeat replaceAll startsWith toWellFormed trim trimEnd trimLeft trimRight trimStart"
  };
  var OWNERS = {
    "": g, Array: NArray, "Array.prototype": AP, "Date.prototype": DP, Error: JError,
    "Function.prototype": FP, Math: NMath, Number: NNumber, Object: NObject, "Object.prototype": OP,
    RegExp: JRegExp, "RegExp.prototype": RP, String: JString, "String.prototype": SP
  };
  for (var owner in REMOVE) {
    var names = REMOVE[owner].split(" ");
    for (var i = 0; i < names.length; i++) {
      try { delete OWNERS[owner][names[i]]; } catch (ignored) {}
    }
  }

  var GLOBAL_SHADOWS = ["toString", "valueOf", "toLocaleString", "hasOwnProperty", "propertyIsEnumerable", "isPrototypeOf"];
  for (var gs = 0; gs < GLOBAL_SHADOWS.length; gs++) {
    defineProperty(g, GLOBAL_SHADOWS[gs], { value: undefined, writable: true, enumerable: false, configurable: true });
  }

  var NAMED = [NObject, NArray, NNumber, JNumber, NMath, g, JString, JRegExp, JDate, JFunction, JError, JTypeError,
    JRangeError, JSyntaxError, JURIError, JEvalError, JReferenceError, JEnumerator, OP, AP, SP, NP, DP, RP, FP, EP,
    Boolean.prototype, Boolean];
  for (var ni = 0; ni < NAMED.length; ni++) {
    var target = NAMED[ni];
    var props = getOwnPropertyNames(target);
    for (var pi = 0; pi < props.length; pi++) {
      var desc;
      try { desc = target[props[pi]]; } catch (ignored) { continue; }
      if (typeof desc === "function") {
        if (!natives.has(desc)) natives.set(desc, props[pi]);
        try { delete desc.name; } catch (ignored) {}
      }
    }
    if (typeof target === "function") {
      try { delete target.name; } catch (ignored) {}
    }
  }

  var api = {
    tof: typeOf, ae: argsEnter, ax: argsExit,
    typeError: function (message, number) { return jerr(NTypeError, message, number); },
    add: add, key: key, get: get, mth: mth, cget: cget, call: callMember, fcall: callFunction, tk: tick,
    fi: forInTarget, fiter: forInIterator, ctor: ctor, i: int64, dn: dropNames,
    ev: evalSource, re: literalRegex, err: function (e) {
      if (e === ABORT) throw e;
      return norm(e);
    },
    norm: norm, hostError: hostError,
    fnmap: function (m) { for (var k in m) if (hasOwn.call(m, k)) fnmap[k] = m[k]; }
  };
  // Frozen so a script cannot replace the loop-abort hook (api.tk) with a no-op (see host.js).
  // nativeFreeze is captured above because the ES3 cleanup deletes Object.freeze.
  nativeFreeze(api);
  defineProperty(g, "__xk", { value: api, enumerable: false, configurable: false, writable: false });
})(this);
