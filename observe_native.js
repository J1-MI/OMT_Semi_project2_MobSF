// observe_native.js
(function () {
  function safeStr(p) {
    try {
      if (!p || p.isNull()) return "<NULL>";
      return Memory.readUtf8String(p);
    } catch (e) {
      return "<READ_ERR>";
    }
  }

  // 각 함수마다 경로 인자 위치가 다름
  var targets = [
    { name: "open",  lib: "libc.so", pathArg: 0 },
    { name: "openat",lib: "libc.so", pathArg: 1 },
    { name: "access",lib: "libc.so", pathArg: 0 },
    { name: "__system_property_get", lib: "libc.so", pathArg: 0 },
    { name: "ptrace", lib: "libc.so", pathArg: null }, // 경로 없음
  ];

  targets.forEach(function (t) {
    try {
      var addr = Module.findExportByName(t.lib, t.name);
      if (!addr) return;

      Interceptor.attach(addr, {
        onEnter: function (args) {
          try {
            if (t.name === "ptrace") {
              this.req = args[0].toInt32();
              console.log("[observe_native] ptrace(req=" + this.req + ")");
              return;
            }

            if (t.pathArg !== null) {
              var p = safeStr(args[t.pathArg]);
              console.log("[observe_native] " + t.name + "(" + p + ")");
            } else {
              console.log("[observe_native] " + t.name + "(...)");
            }
          } catch (e) {
            console.log("[observe_native] " + t.name + " enter err: " + e);
          }
        }
      });

      console.log("[observe_native] hooked " + t.name);
    } catch (e) {
      console.log("[observe_native] hook err for " + t.name + ": " + e);
    }
  });
})();
