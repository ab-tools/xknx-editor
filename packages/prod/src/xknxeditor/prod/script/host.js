(function (g) {
  var callPython = g.call_python;
  var defineProperty = Object.defineProperty;
  var hasOwn = Object.prototype.hasOwnProperty;
  var isArray = Array.isArray;
  var fnApply = Function.prototype.apply;
  var ABORT = { aborted: true };

  function makeError(e) {
    if (g.__xk) return g.__xk.hostError(e.message, e.number);
    var err = new Error(e.message);
    if (e.number !== undefined && e.number !== null) err.number = e.number;
    err.description = e.message;
    return err;
  }

  function decode(v) {
    if (v !== null && typeof v === "object") {
      if (hasOwn.call(v, "$num")) return Number(v.$num);
      if (isArray(v)) {
        var a = [];
        for (var i = 0; i < v.length; i++) a.push(decode(v[i]));
        return a;
      }
      var o = {};
      for (var k in v) if (hasOwn.call(v, k)) o[k] = decode(v[k]);
      return o;
    }
    return v;
  }

  function plain(v, depth) {
    depth = depth || 0;
    if (v === null || v === undefined) return null;
    var t = typeof v;
    if (t === "number") return isFinite(v) ? v : { $num: String(v) };
    if (t === "string" || t === "boolean") return v;
    if (t === "function" || depth > 16) return null;
    if (isArray(v)) {
      var a = [];
      for (var i = 0; i < v.length; i++) a.push(plain(v[i], depth + 1));
      return a;
    }
    var o = {};
    for (var k in v) if (hasOwn.call(v, k)) o[k] = plain(v[k], depth + 1);
    return o;
  }

  function host(name) {
    var args = [name];
    for (var i = 1; i < arguments.length; i++) args.push(plain(arguments[i]));
    var r = fnApply.call(callPython, null, args);
    if (r === null || r === undefined) return undefined;
    if (r.a) throw ABORT;
    if (hasOwn.call(r, "e")) throw makeError(r.e);
    return decode(r.v);
  }

  function method(f) {
    defineProperty(f, "__xk_unknown", { value: true });
    return f;
  }

  function methods(o) {
    for (var k in o) if (hasOwn.call(o, k) && typeof o[k] === "function") method(o[k]);
    return o;
  }

  function param(ref) {
    if (ref === null || ref === undefined) return null;
    var p = {};
    defineProperty(p, "value", {
      get: function () { return host("p.get", ref); },
      set: function (v) { host("p.set", ref, v); }
    });
    defineProperty(p, "isActive", { get: function () { return host("p.active", ref); } });
    defineProperty(p, "parameterRefId", { get: function () { return host("p.ref", ref); } });
    defineProperty(p, "name", { get: function () { return host("p.name", ref); } });
    return p;
  }

  function device(scope) {
    var d = {
      getParameterByName: function (name) { return param(host("d.byName", scope, name)); },
      getParameterById: function (id) { return param(host("d.byId", scope, id)); },
      getParameterByUniqueNumber: function (n) { return param(host("d.byNumber", scope, n)); },
      getMessage: function (id) {
        var m = host("d.message", id);
        return m === null ? undefined : m;
      },
      withUndo: function (description, fn) {
        host("d.undoBegin", description === undefined ? "" : String(description));
        try {
          fn();
        } catch (e) {
          if (e !== ABORT) host("d.undoRollback");
          throw e;
        }
        host("d.undoCommit");
      }
    };
    methods(d);
    defineProperty(d, "ApplicationProgramName", { get: function () { return host("d.appName"); } });
    return d;
  }

  var ONLINE = [
    "connect", "disconnect", "readDeviceDescriptor0", "getMaxApduLength",
    "locateInterfaceObject", "readFunctionProperty", "invokeFunctionProperty",
    "readProperty", "writeProperty", "readMemory", "writeMemory", "readUserMemory",
    "writeUserMemory", "restart", "coapReadCollection", "coapGet", "coapPut", "coapPost"
  ];

  function online() {
    var o = {};
    for (var i = 0; i < ONLINE.length; i++) {
      o[ONLINE[i]] = (function (n) {
        return function () {
          var a = ["o." + n];
          for (var j = 0; j < arguments.length; j++) a.push(arguments[j]);
          return fnApply.call(host, null, a);
        };
      })(ONLINE[i]);
    }
    return methods(o);
  }

  function progress() {
    return methods({
      setProgress: function (v) { host("g.progress", Number(v)); },
      setText: function (t) { host("g.text", t === undefined ? "" : String(t)); },
      isCanceled: function () { return host("g.canceled"); }
    });
  }

  function logger(level) {
    return method(function (msg) { host("log", level, msg === undefined || msg === null ? "" : String(msg)); });
  }

  function resolve(a) {
    if (a !== null && typeof a === "object" && hasOwn.call(a, "$host")) {
      if (a.$host === "device") return device(a.scope);
      if (a.$host === "online") return online();
      if (a.$host === "progress") return progress();
      if (a.$host === "undefined") return undefined;
      return null;
    }
    return decode(a);
  }

  function describe(e) {
    if (g.__xk) e = g.__xk.norm(e);
    if (e !== null && typeof e === "object") {
      return {
        name: String(e.name),
        message: String(e.message),
        number: typeof e.number === "number" ? e.number : null,
        stack: typeof e.stack === "string" ? e.stack : null
      };
    }
    return { name: "Error", message: String(e), number: null, stack: null };
  }

  var api = {
    install: function (globalsSpec) {
      var log = { error: logger("error"), warn: logger("warn"), info: logger("info"), Debug: logger("error") };
      g.Log = log;
      g.error = log.error;
      g.warn = log.warn;
      g.info = log.info;
      g.Debug = log.Debug;
      if (globalsSpec && globalsSpec.getMessage) {
        g.getMessage = method(function (id) { return host("a.message", id); });
      }
    },
    invoke: function (fn, args, readback) {
      try { delete g.dukpy; delete g.call_python; } catch (ignored) {}
      var f = g[fn];
      if (typeof f !== "function") {
        return { x: { name: "TypeError", message: "'" + fn + "' is undefined", number: -2146823279, stack: null } };
      }
      var real = [];
      for (var i = 0; i < args.length; i++) real.push(resolve(args[i]));
      try {
        var ret = fnApply.call(f, undefined, real);
        var out = { r: plain(ret), b: [] };
        if (readback) for (var j = 0; j < readback.length; j++) out.b.push(plain(real[readback[j]]));
        return out;
      } catch (e) {
        if (e === ABORT) return { a: 1 };
        return { x: describe(e) };
      }
    },
    tick: function () { host("__tick"); },
    isAbort: function (e) { return e === ABORT; },
    host: host,
    plain: plain,
    abort: ABORT
  };

  defineProperty(g, "__xknx__", { value: api, enumerable: false, configurable: false, writable: false });
})(this);
