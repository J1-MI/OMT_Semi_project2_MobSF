#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MobSF 기반 OMT CLI 프런트엔드
- python main.py  (대화형)
- python main.py --mode static  --apk mobsf_ext/static/samples/UnCrackable-Level1.apk
- python main.py --mode dynamic --apk mobsf_ext/static/samples/UnCrackable-Level1.apk [--host 127.0.0.1 --port 27042] [--spawn]
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

# --------- ASCII 배너 ----------
BANNER = r"""
 ________  _____ ______   _________                    
|\   __  \|\   _ \  _   \|\___   ___\                  
\ \  \|\  \ \  \\\__\ \  \|___ \  \_|                  
 \ \  \\\  \ \  \\|__| \  \   \ \  \                   
  \ \  \\\  \ \  \    \ \  \   \ \  \                  
   \ \_______\ \__\    \ \__\   \ \__\                 
    \|_______|\|__|     \|__|    \|__|                 
                                                       
                                                       
                                                       
                    ___    ___                         
                   |\  \  /  /|                        
                   \ \  \/  / /                        
                    \ \    / /                         
                     /     \/                          
                    /  /\   \                          
                   /__/ /\ __\                         
                   |__|/ \|__|                         
                                                       
                                                       
 _____ ______   ________  ________  ________  ________ 
|\   _ \  _   \|\   __  \|\   __  \|\   ____\|\  _____\
\ \  \\\__\ \  \ \  \|\  \ \  \|\ /\ \  \___|\ \  \__/ 
 \ \  \\|__| \  \ \  \\\  \ \   __  \ \_____  \ \   __\
  \ \  \    \ \  \ \  \\\  \ \  \|\  \|____|\  \ \  \_|
   \ \__\    \ \__\ \_______\ \_______\____\_\  \ \__\ 
    \|__|     \|__|\|_______|\|_______|\_________\|__| 
                                      \|_________|     
                                                       
                                                       
"""

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 27042
DEFAULT_SECS = int(os.environ.get("TEST_SECS", "60"))

ROOT = Path(__file__).resolve().parent
LOGS_DIR = ROOT / "outputs"
RUN_DYNAMIC = ROOT / "run_dynamic_test_safe.py"

# --------- 유틸 ----------
def c(s, color="32"):
    return f"\033[{color}m{s}\033[0m"  # 32=초록, 31=빨강, 33=노랑, 36=하늘

def sh(cmd, check=False, capture=False):
    kwargs = dict(text=True)
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
    return subprocess.run(cmd, check=check, **kwargs)

def ensure_module(modname, pip_name=None):
    try:
        __import__(modname)
        return True
    except ImportError:
        print(c(f"[!] Python 모듈이 없습니다: {modname}", "31"))
        if pip_name:
            print(f"    -> 설치: {c(f'pip install {pip_name}', '33')}")
        return False

def guess_package_from_apk(apk_path: Path) -> str | None:
    # 1) androguard 우선
    try:
        from androguard.core.bytecodes.apk import APK
        return APK(str(apk_path)).get_package()
    except Exception:
        pass
    # 2) aapt(또는 aapt2) 보조
    aapt = shutil.which("aapt") or shutil.which("aapt2")
    if aapt:
        try:
            out = sh([aapt, "dump", "badging", str(apk_path)], capture=True).stdout
            for tok in out.split():
                if tok.startswith("name="):
                    return tok.split("=", 1)[1].strip("'\"")
        except Exception:
            pass
    return None

def frida_preflight(host: str, port: int) -> bool:
    # TCP 핑
    try:
        s = socket.socket()
        s.settimeout(2)
        s.connect((host, port))
        s.close()
    except Exception as e:
        print(c(f"[!] {host}:{port} 접속 실패 - frida-server/포워딩 확인 필요: {e}", "31"))
        return False
    # frida-tools 있으면 ps 한 번
    if ensure_module("frida_tools", "frida-tools"):
        try:
            sh([sys.executable, "-m", "frida_tools.ps", "-H", f"{host}:{port}"], check=False)
        except Exception:
            pass
    return True

# --------- Static ----------
def run_static(apk_path: Path):
    print(c("\n[ Static Analysis ]", "36"))
    if not ensure_module("androguard", "androguard==3.3.5"):
        print(c(" androguard 설치 후 다시 실행하세요.", "31"))
        return 1

    # 내부 디텍터 사용
    try:
        from mobsf_ext.static.detectors.manifest_check import manifest_findings
        from mobsf_ext.static.detectors.dex_hidden import find_hidden_dex
        from mobsf_ext.static.detectors.dynamic_loading import (
            detect_dynamic_loading_markers, find_native_libs
        )
    except Exception as e:
        print(c(f"[!] 디텍터 임포트 실패: {e}", "31"))
        return 1

    try:
        report = {
            "apk": str(apk_path),
            "package": guess_package_from_apk(apk_path),
            "manifest": manifest_findings(apk_path),
            "hidden_dex": find_hidden_dex(apk_path),
            "dyn_loading": detect_dynamic_loading_markers(apk_path),
            "native_libs": find_native_libs(apk_path),
        }
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        out_json = LOGS_DIR / f"{apk_path.stem}_static.json"
        out_txt  = LOGS_DIR / f"{apk_path.stem}_static.txt"
        out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        out_txt.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        print(c(f" ✓ 보고서 저장: {out_json}", "32"))
        print(c(" 요약:", "36"))
        print("  - package:", report["package"])
        print("  - dangerous perms:", report["manifest"].get("dangerous_permissions"))
        print("  - hidden_dex:", report["hidden_dex"])
        print("  - dyn_loading_markers:", report["dyn_loading"])
        print("  - native_libs:", report["native_libs"])
        return 0
    except Exception as e:
        print(c(f"[!] Static 실패: {e}", "31"))
        return 1

# --------- Dynamic ----------
def run_dynamic(apk_path: Path, host: str, port: int, secs: int, spawn: bool):
    print(c("\n[ Dynamic Analysis ]", "36"))
    if not RUN_DYNAMIC.exists():
        print(c(f"[!] {RUN_DYNAMIC.name} 를 찾지 못했습니다. 루트에 파일이 있어야 합니다.", "31"))
        return 1
    if not frida_preflight(host, port):
        return 1

    # 설치 (이미 설치되어 있으면 -r 로 재설치)
    print(c(" - adb install...", "33"))
    sh(["adb", "install", "-r", str(apk_path)], check=False)

    pkg = guess_package_from_apk(apk_path)
    if not pkg:
        print(c("[!] 패키지명을 추출하지 못했습니다. --pkg를 직접 넣어 실행해주세요.", "31"))
        return 1

    # 로그 경로
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    dyn_log = LOGS_DIR / f"{apk_path.stem}_dynamic.log"

    cmd = [
        sys.executable, str(RUN_DYNAMIC),
        "--pkg", pkg,
        "--log", str(dyn_log),
        "--host", host, "--port", str(port),
    ]
    if spawn:
        cmd.insert(2, "--spawn")

    print(c(f" - run: {' '.join(cmd)}", "33"))
    # 주의: run_dynamic_test_safe.py 내부에서 adb를 reset하지 않도록 최신 버전으로 수정되어 있어야 함
    proc = sh(cmd, check=False)
    if proc.returncode == 0:
        print(c(f" ✓ 동적 로그: {dyn_log}", "32"))
        # 마지막 10줄 미리 보여주기
        try:
            tail = dyn_log.read_text(encoding="utf-8", errors="ignore").splitlines()[-10:]
            print(c(" --- tail(log) ---", "36"))
            print("\n".join(tail))
        except Exception:
            pass
        return 0
    else:
        print(c(f"[!] Dynamic 실패 (code={proc.returncode})", "31"))
        return proc.returncode

# --------- 대화형 ----------
def interactive():
    print(c(BANNER, "36"))
    print("모드를 선택하세요:")
    print("  1) Static Analysis")
    print("  2) Dynamic Analysis")
    print("  0) Exit")
    sel = input("> ").strip()

    if sel == "0":
        return 0
    if sel not in {"1", "2"}:
        print(c("[!] 잘못된 선택입니다.", "31"))
        return 1

    apk = input("APK 경로를 입력하세요: ").strip().strip('"')
    apk_path = Path(apk).expanduser().resolve()
    if not apk_path.exists():
        print(c(f"[!] APK가 존재하지 않습니다: {apk_path}", "31"))
        return 1

    if sel == "1":
        return run_static(apk_path)

    # dynamic
    host = input(f"Frida host [{DEFAULT_HOST}]: ").strip() or DEFAULT_HOST
    port_s = input(f"Frida port [{DEFAULT_PORT}]: ").strip() or str(DEFAULT_PORT)
    try:
        port = int(port_s)
    except ValueError:
        print(c("[!] 포트는 숫자여야 합니다.", "31"))
        return 1

    secs_s = input(f"실행 시간(초) [{DEFAULT_SECS}]: ").strip() or str(DEFAULT_SECS)
    try:
        secs = int(secs_s)
    except ValueError:
        secs = DEFAULT_SECS

    spawn = input("Spawn 모드로 실행할까요? (y/N): ").strip().lower().startswith("y")
    return run_dynamic(apk_path, host, port, secs, spawn)

# --------- 메인 ----------
def main():
    parser = argparse.ArgumentParser(description="OMT + MobSF CLI Runner")
    parser.add_argument("--mode", choices=["static", "dynamic"], help="분석 모드")
    parser.add_argument("--apk", help="APK 경로")
    parser.add_argument("--host", default=DEFAULT_HOST, help="frida-server host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="frida-server port")
    parser.add_argument("--secs", type=int, default=DEFAULT_SECS, help="동적 실행 시간(초)")
    parser.add_argument("--spawn", action="store_true", help="spawn 후 attach (권장)")
    args = parser.parse_args()

    # 색상 지원(윈도우 구터미널/파워쉘 대부분 OK)
    print(c(BANNER, "36"))

    if not args.mode or not args.apk:
        # 대화형
        sys.exit(interactive())

    apk_path = Path(args.apk).expanduser().resolve()
    if not apk_path.exists():
        print(c(f"[!] APK가 존재하지 않습니다: {apk_path}", "31"))
        sys.exit(1)

    if args.mode == "static":
        rc = run_static(apk_path)
    else:
        rc = run_dynamic(apk_path, args.host, args.port, args.secs, args.spawn)
    sys.exit(rc)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n종료합니다.")
