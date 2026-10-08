import sys
import os
import subprocess
import signal
import socket
import json
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PID_FILE = BASE_DIR / ".dropsync.pid"
PORT = 8080

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

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
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if is_running(pid):
                print(f"[!] DropSync Pro is already running (PID: {pid})")
                print(f" -> Local:  http://localhost:{PORT}")
                print(f" -> LAN IP: http://{get_lan_ip()}:{PORT}")
                return
        except Exception:
            pass

    print("[*] Starting DropSync Pro Engine in background...")
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
    print(f" -> Local:  http://localhost:{PORT}")
    print(f" -> LAN IP: http://{get_lan_ip()}:{PORT}")
    print(f" -> Security PIN: 1234 (default)")

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
    if not PID_FILE.exists():
        print("Status: 🔴 STOPPED")
        return

    pid = int(PID_FILE.read_text().strip())
    if is_running(pid):
        print(f"Status: 🟢 RUNNING (PID: {pid})")
        print(f" -> Web Portal: http://localhost:{PORT}")
        print(f" -> LAN Access: http://{get_lan_ip()}:{PORT}")
    else:
        print("Status: 🔴 STOPPED (stale PID file cleaned up)")
        PID_FILE.unlink()

def cmd_gui():
    print("[*] Launching DropSync Pro GUI Engine Monitor...")
    subprocess.Popen([sys.executable, str(BASE_DIR / "controller.py")], cwd=str(BASE_DIR))

def main():
    if len(sys.argv) < 2:
        print("""
DropSync Pro CLI & Controller
-----------------------------
Usage:
  py cli.py start    - Start DropSync Pro in the background
  py cli.py stop     - Stop the background server
  py cli.py restart  - Restart DropSync Pro
  py cli.py status   - Check if server is running and get IP links
  py cli.py gui      - Open the desktop Engine Monitor GUI
        """)
        return

    action = sys.argv[1].lower()
    if action == "start":
        cmd_start()
    elif action == "stop":
        cmd_stop()
    elif action == "restart":
        cmd_stop()
        cmd_start()
    elif action == "status":
        cmd_status()
    elif action in ("gui", "ui", "controller"):
        cmd_gui()
    else:
        print(f"[!] Unknown command '{action}'. Use start, stop, restart, status, or gui.")

if __name__ == "__main__":
    main()
