// bypass_native.js
(function () {
  var propMap = {
    "ro.kernel.qemu": "0",
    "ro.debuggable": "0",
    "ro.product.model": "Pixel 7"
  };

  // __system_property_get(const char* name, char* value) -> int (len)
  try {
    var pget = Module.findExportByName("libc.so", "__system_property_get");
    if (pget) {
      Interceptor.attach(pget, {
        onEnter: function (args) {
          this.key = null;
          this.buf = null;
          try { this.key = Memory.readUtf8String(args[0]); } catch (e) {}
          try { this.buf = args[1]; } catch (e) {}
        },
        onLeave: function (ret) {
          try {
            if (this.key && propMap[this.key] && this.buf && !this.buf.isNull()) {
              var v = propMap[this.key];
              Memory.writeUtf8String(this.buf, v);
              ret.replace(v.length); // 반환값은 길이
              console.log("[bypass_native] __system_property_get(" + this.key + ") -> " + v);
            }
          } catch (e) {
            console.log("[bypass_native] __system_property_get err: " + e);
          }
        }
      });
      console.log("[bypass_native] hooked __system_property_get");
    }
  } catch (e) {
    console.log("[bypass_native] __system_property_get hook err: " + e);
  }

  // ptrace 방어: PTRACE_TRACEME(0) 시도는 성공(0)으로 위조
  try {
    var pptrace = Module.findExportByName("libc.so", "ptrace");
    if (pptrace) {
      Interceptor.attach(pptrace, {
        onEnter: function (args) {
          this.req = args[0].toInt32();
        },
        onLeave: function (ret) {
          try {
            if (this.req === 0) { // PTRACE_TRACEME
              ret.replace(0);
              console.log("[bypass_native] ptrace(TRACEME) -> 0");
            }
          } catch (e) {
            console.log("[bypass_native] ptrace onLeave err: " + e);
          }
        }
      });
      console.log("[bypass_native] hooked ptrace");
    }
  } catch (e) {
    console.log("[bypass_native] ptrace hook err: " + e);
  }

  // 루트 흔적 숨김 (open/access)
  try {
    ["open", "access", "openat"].forEach(function (name) {
      var addr = Module.findExportByName("libc.so", name);
      if (!addr) return;

      Interceptor.attach(addr, {
        onEnter: function (args) {
          // open: path=0, access: path=0, openat: path=1
          var idx = (name === "openat") ? 1 : 0;
          this.p = null;
          try { this.p = Memory.readUtf8String(args[idx]); } catch (e) {}
        },
        onLeave: function (ret) {
          try {
            if (!this.p) return;
            var path = this.p.toLowerCase();
            if (path.indexOf("/su") >= 0 || path.indexOf("magisk") >= 0) {
              // 접근 숨김: 실패(-1)로 위조
              ret.replace(-1);
              console.log("[bypass_native] " + name + " hide " + this.p);
            }
          } catch (e) {
            console.log("[bypass_native] " + name + " onLeave err: " + e);
          }
        }
      });

      console.log("[bypass_native] hooked " + name);
    });
  } catch (e) {
    console.log("[bypass_native] open/access hook err: " + e);
  }
})();
