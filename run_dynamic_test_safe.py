#!/usr/bin/env python3
import argparse
import frida
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# -----------------------------
# Defaults (옵션으로 덮어쓸 수 있음)
# -----------------------------
DEFAULT_PKG = "com.android.quicksearchbox"
DEFAULT_ACTIVITY = f"{DEFAULT_PKG}/.SearchActivity"
DEFAULT_SECS = int(os.environ.get("TEST_SECS", "60"))

JS_SCRIPTS = [
    Path(__file__).with_name("observe_java_safe.js"),
    Path(__file__).with_name("observe_native.js"),
    Path(__file__).with_name("bypass_java.js"),
    Path(__file__).with_name("bypass_native.js"),
]

BASE_LOG_DIR = Path("logs")


# -----------------------------
# Helpers
# -----------------------------
def run(cmd, check=False, capture=False):
    kwargs = dict(text=True)
    if capture:
        kwargs.update(dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
    return subprocess.run(cmd, check=check, **kwargs)


def ensure_adb_server():
    """ADB 서버 버전 충돌/미기동을 완화: kill → start → devices"""
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("adb 가 PATH에 없습니다. Android platform-tools 경로를 PATH에 추가하세요.")
    run([adb, "kill-server"])
    run([adb, "start-server"])
    out = run([adb, "devices"], capture=True).stdout.strip()
    return out


def wait_for_device():
    """adb로 디바이스 연결 대기(에뮬레이터 포함)"""
    run(["adb", "wait-for-device"])
    out = run(["adb", "devices"], capture=True).stdout
    if "device" not in out:
        raise RuntimeError("adb에 연결된 장치가 없습니다. (에뮬/실기기 연결 확인)")
    return out


def get_device(host: str, port: int):
    """지정한 host:port의 원격 frida-server로 접속"""
    return frida.get_device_manager().add_remote_device(f"{host}:{port}")


def log_write(fp: Path, line: str):
    ts = time.strftime("%H:%M:%S")
    s = f"[{ts}] {line}"
    print(s)
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def on_message_factory(fp: Path):
    def on_message(msg, data):
        if msg.get("type") == "send":
            log_write(fp, f"[FRIDA] {msg.get('payload')}")
        elif msg.get("type") == "error":
            log_write(fp, f"[FRIDA-ERR] {msg.get('stack')}")
        else:
            log_write(fp, f"[FRIDA-DBG] {msg}")
    return on_message

def ensure_forward(port: int):
    # kill-server 이후 포워딩이 날아가므로 항상 재설정
    run(["adb", "forward", "--remove-all"])
    run(["adb", "forward", f"tcp:{port}", f"tcp:{port}"])

def ensure_forward(port: int):
    # 포워딩이 없을 수 있으니 항상 보장
    run(["adb", "forward", f"tcp:{port}", f"tcp:{port}"])
    
# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Safe dynamic test runner (Frida attach/spawn, emulator/USB 원격 접속 지원)"
    )
    parser.add_argument("--pkg", default=DEFAULT_PKG, help="테스트할 앱 패키지명")
    parser.add_argument("--activity", default=DEFAULT_ACTIVITY, help="메인 액티비티 (am start용)")
    parser.add_argument("--secs", type=int, default=DEFAULT_SECS, help="실행 시간(초)")
    parser.add_argument("--spawn", action="store_true", help="Frida로 spawn 후 attach (권장)")
    parser.add_argument("--log", default=None, help="로그 파일 경로(기본: logs/<pkg>/dynamic_log_<ts>.txt)")
    parser.add_argument("--host", default="127.0.0.1", help="frida-server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=27043, help="frida-server port (default: 27043)")
    parser.add_argument("--adb-reset", action="store_true",help="실행 시 adb kill-server/start-server를 수행 (기본 비활성화)")
    args = parser.parse_args()

    # 로그 파일 준비
    log_dir = BASE_LOG_DIR / args.pkg
    log_fp = Path(args.log) if args.log else (log_dir / f"dynamic_log_{time.strftime('%Y%m%d_%H%M%S')}.txt")
    print(f"[*] Dynamic Test Start - Target: {args.pkg}")
    print(f"[*] Logs will be saved to {log_fp}")

    '''
    # 0) ADB 서버/디바이스 확인(일반 이슈 완화)
    try:
        ensure_adb_server()
        wait_for_device()
    except Exception as e:
        print(f"[!] adb 준비 실패: {e}")
    '''
    # 0) ADB 서버/디바이스 확인
    try:
        if args.adb_reset:
            ensure_adb_server()      # 사용자가 명시한 경우에만 kill/start
        wait_for_device()             # 장치 연결 대기만 수행 (kill/start 하지 않음)
        ensure_forward(args.port)     # 포워딩 보장 (remove-all은 하지 않음)
    except Exception as e:
        print(f"[!] adb 준비 경고: {e}")
    
    # 1) 앱 재시작 준비
    #   spawn을 쓸 거면 'am start'는 굳이 하지 않음(중복 실행 방지)
    run(["adb", "shell", "am", "force-stop", args.pkg])

    # 2) 장치 획득 (원격 frida-server)
    device = get_device(args.host, args.port)

    # 3) 세션 생성
    try:
        if args.spawn:
            pid = device.spawn([args.pkg])
            session = device.attach(pid)
            device.resume(pid)
            time.sleep(1)
        else:
            raise RuntimeError("skip_spawn")
    except Exception:
    # spawn 실패 → 앱 실행 후 attach 폴백
        run(["adb", "shell", "monkey", "-p", args.pkg, "-c", "android.intent.category.LAUNCHER", "1"])
        time.sleep(2)
        procs = {p.name: p.pid for p in device.enumerate_processes()}
        if args.pkg not in procs:
            raise RuntimeError(f"실행 중인 프로세스에서 {args.pkg} 를 찾지 못했습니다.")
        pid = procs[args.pkg]
        session = device.attach(pid)
    '''
    if args.spawn:
        pid = device.spawn([args.pkg])
        session = device.attach(pid)
    else:
        # 기존 프로세스 기동 후 attach
        run(["adb", "shell", "am", "start", "-n", args.activity])
        time.sleep(2)
        procs = {p.name: p.pid for p in device.enumerate_processes()}
        if args.pkg not in procs:
            raise RuntimeError(f"실행 중인 프로세스에서 {args.pkg} 를 찾지 못했습니다.")
        pid = procs[args.pkg]
        session = device.attach(pid)
    '''
    # 4) JS 스크립트 로드
    on_message = on_message_factory(log_fp)
    for js in JS_SCRIPTS:
        if not js.exists():
            log_write(log_fp, f"[WARN] JS not found: {js}")
            continue
        script = session.create_script(js.read_text(encoding="utf-8"))
        script.on("message", on_message)
        script.load()
        log_write(log_fp, f"[*] Loaded {js.name}")

    # 5) 실행
    if args.spawn:
        device.resume(pid)
        time.sleep(1)  # 첫 프레임 로딩 여유

    log_write(log_fp, f"[*] Running dynamic test for {args.secs}s...")
    time.sleep(args.secs)
    log_write(log_fp, "[*] Test finished")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"[!] ERROR: {e}")
        sys.exit(1)
