// observe_java_safe.js
(function () {
    function hookJava() {
      try {
        var Build = Java.use("android.os.Build");
        console.log("[observe_java] Build.MODEL=" + Build.MODEL.value +
                    " PRODUCT=" + Build.PRODUCT.value);
      } catch (e) {
        console.log("[observe_java] Build hook err: " + e);
      }
  
      try {
        var System = Java.use("java.lang.System");
        System.getProperty.overload('java.lang.String').implementation = function (key) {
          var ret = this.getProperty(key);
          console.log("[observe_java] System.getProperty(" + key + ") -> " + ret);
          return ret;
        };
      } catch (e) {
        console.log("[observe_java] System.getProperty hook err: " + e);
      }
  
      try {
        var SP = Java.use("android.os.SystemProperties");
        SP.get.overload('java.lang.String').implementation = function (k) {
          var ret = this.get(k);
          console.log("[observe_java] SystemProperties.get(" + k + ") -> " + ret);
          return ret;
        };
      } catch (e) {
        console.log("[observe_java] SystemProperties.get hook err: " + e);
      }
  
      try {
        var Debug = Java.use("android.os.Debug");
        Debug.isDebuggerConnected.implementation = function () {
          var r = this.isDebuggerConnected();
          console.log("[observe_java] Debug.isDebuggerConnected() -> " + r);
          return r;
        };
      } catch (e) {
        console.log("[observe_java] Debug.isDebuggerConnected hook err: " + e);
      }
  
      try {
        var File = Java.use("java.io.File");
        File.exists.implementation = function () {
          var path, r;
          try { path = this.getPath(); } catch (e) { path = "<unknown>"; }
          try { r = this.exists(); } catch (e) { r = "<err>"; }
          console.log("[observe_java] File.exists(" + path + ") -> " + r);
          return r;
        };
      } catch (e) {
        console.log("[observe_java] File.exists hook err: " + e);
      }
  
      console.log("[observe_java] Hooks applied");
    }
  
    function tryHook() {
      if (typeof Java !== "undefined" && Java.available) {
        Java.perform(hookJava);
      } else {
        // VM 준비되기 전이면 조금 뒤에 재시도
        setTimeout(tryHook, 500);
      }
    }
  
    tryHook();
  })();
  