import sys
import os
import subprocess
import signal
import socket
import json
import urllib.request
from pathlib import Path

from config_manager import load_config, save_config

BASE_DIR = Path(__file__).resolve().parent
PID_FILE = BASE_DIR / ".dropsync.pid"

def get_lan_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(('8.8.8.8', 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips or ["127.0.0.1"]

def is_running(pid):
    if not pid:
        return False
    try:
        if os.name == 'nt':
            output = subprocess.check_output(f'tasklist /FI "PID eq {pid}" /NH', shell=True).decode()
            return str(pid) in output
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def cmd_start():
    cfg = load_config()
    port = cfg.get("port", 8080)
    pin = cfg.get("pin", "")

    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if is_running(pid):
                print(f"[!] DropSync Pro is already running (PID: {pid})")
                print(f" -> Local:  http://localhost:{port}")
                print(f" -> LAN IP: http://{get_lan_ips()[0]}:{port}")
                print(f" -> Security PIN: {pin}")
                return
        except Exception:
            pass

    print("[*] Starting DropSync Pro Engine...")
    cmd = [sys.executable, str(BASE_DIR / "app.py")]
    
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setpgrp
        )

    PID_FILE.write_text(str(proc.pid))
    print(f"[✓] DropSync Pro started successfully (PID: {proc.pid})")
    print(f" -> Local:  http://localhost:{port}")
    print(f" -> LAN IP: http://{get_lan_ips()[0]}:{port}")
    print(f" -> Security PIN: {pin}")

def cmd_stop():
    if not PID_FILE.exists():
        print("[-] DropSync Pro is not running.")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        if is_running(pid):
            print(f"[*] Stopping DropSync Pro (PID: {pid})...")
            if os.name == 'nt':
                subprocess.call(f"taskkill /F /T /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.kill(pid, signal.SIGTERM)
            print("[✓] DropSync Pro has been stopped.")
        else:
            print("[-] DropSync Pro process not found (already stopped).")
    except Exception as e:
        print(f"[!] Error stopping server: {e}")
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()

def cmd_status():
    cfg = load_config()
    port = cfg.get("port", 8080)
    pin = cfg.get("pin", "")

    if not PID_FILE.exists():
        print("Status: 🔴 STOPPED")
        return

    pid = int(PID_FILE.read_text().strip())
    if is_running(pid):
        print(f"Status: 🟢 RUNNING (PID: {pid})")
        print(f" -> Local URL:   http://localhost:{port}")
        for ip in get_lan_ips():
            print(f" -> LAN URL:     http://{ip}:{port}")
        print(f" -> PIN Code:    {pin}")
        # Fetch device count
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/engine/monitor")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode())
                devs = len(data.get("connected_devices", []))
                print(f" -> Active Devices: {devs}")
        except Exception:
            pass
    else:
        print("Status: 🔴 STOPPED (stale PID cleaned up)")
        PID_FILE.unlink()

def cmd_pin(args):
    cfg = load_config()
    if len(args) > 0 and args[0] == "reset":
        import secrets
        new_pin = f"{secrets.randbelow(900000) + 100000}"
        cfg["pin"] = new_pin
        save_config(cfg)
        print(f"[✓] New Security PIN generated: {new_pin}")
        print("Restart server (`dropsync restart`) to apply.")
    else:
        print(f"Current Security PIN: {cfg.get('pin', 'Not set')}")

def cmd_devices():
    cfg = load_config()
    port = cfg.get("port", 8080)
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/engine/monitor")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            devs = data.get("connected_devices", [])
            print(f"Connected Devices ({len(devs)}):")
            for d in devs:
                status_str = "[BLOCKED]" if d.get("blocked") else "[ACTIVE]"
                print(f" - {d.get('name')} ({d.get('ip')}) {status_str} Last seen: {d.get('lastSeen')}")
    except Exception:
        print("[!] Cannot query devices. Is DropSync running? (`dropsync start`)")

def cmd_logs():
    cfg = load_config()
    port = cfg.get("port", 8080)
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/engine/monitor")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            logs = data.get("activity_logs", [])
            print("Recent Audit Logs:")
            for l in logs[:15]:
                print(f"[{l.get('time')}] [{l.get('type').upper()}] {l.get('message')}")
    except Exception:
        print("[!] Server not running or logs unavailable.")

def cmd_open():
    cfg = load_config()
    port = cfg.get("port", 8080)
    import webbrowser
    webbrowser.open(f"http://localhost:{port}")

def cmd_version():
    print("DropSync Pro v2.0.0 (Apple Liquid Glass Architecture)")

def main():
    if len(sys.argv) < 2:
        print("""
DropSync Pro CLI (Unified Engine Command)
=========================================
Commands:
  dropsync start             Start server engine in background
  dropsync stop              Stop background engine
  dropsync restart           Restart server engine
  dropsync status            Show running status, LAN URLs, and devices
  dropsync pin [reset]       Show current PIN or generate a new random 6-digit PIN
  dropsync devices           List connected phones, tablets, and PCs
  dropsync logs              Show live security, upload, and download logs
  dropsync open              Open web dashboard in default browser
  dropsync version           Display version information
        """)
        return

    cmd = sys.argv[1].lower()
    if cmd == "start": cmd_start()
    elif cmd == "stop": cmd_stop()
    elif cmd == "restart": cmd_stop(); cmd_start()
    elif cmd == "status": cmd_status()
    elif cmd == "pin": cmd_pin(sys.argv[2:])
    elif cmd == "devices": cmd_devices()
    elif cmd == "logs": cmd_logs()
    elif cmd == "open": cmd_open()
    elif cmd == "version": cmd_version()
    else:
        print(f"Unknown command '{cmd}'. Run 'dropsync' for help.")

if __name__ == "__main__":
    main()
