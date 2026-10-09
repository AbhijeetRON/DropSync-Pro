"""
dropsync_cli.py — DropSync Pro Command-Line Interface
Runs the server IN-PROCESS (uvicorn.Server in a thread). No subprocess, no py launcher.
"""
import sys
import os
import socket
import json
import time
import threading
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path

from config_manager import load_config, save_config, validate_pin, generate_secure_pin

BASE_DIR = Path(__file__).resolve().parent

# Lock socket port (same one used by the GUI controller)
LOCK_PORT = 49258
# We use a different port range so CLI-launched server can run independently
CLI_LOCK_PORT = 49259

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

def _api(path: str, port: int, method="GET", body: dict = None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()}
    except Exception as e:
        return {"_error": -1, "_msg": str(e)}

def _is_server_up(port: int) -> bool:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/status")
        with urllib.request.urlopen(req, timeout=1.0):
            return True
    except Exception:
        return False

# ─── State file for CLI-launched server (stores port) ──────────────────────────
STATE_FILE = Path(os.getenv("APPDATA", str(Path.home()))) / "DropSyncPro" / ".cli_server_port"

def _write_state(port: int):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(str(port))

def _read_state() -> int | None:
    try:
        return int(STATE_FILE.read_text().strip())
    except Exception:
        return None

def _clear_state():
    try:
        STATE_FILE.unlink(missing_ok=True)
    except Exception:
        pass

# ─── Commands ──────────────────────────────────────────────────────────────────

def cmd_start():
    cfg = load_config()
    port = cfg.get("port", 8080)
    pin = cfg.get("pin", "")

    # Check if already up
    if _is_server_up(port):
        print(f"[!] DropSync Pro is already running.")
        print(f"    Local:  http://localhost:{port}")
        print(f"    LAN:    http://{get_lan_ips()[0]}:{port}")
        print(f"    PIN:    {pin}")
        return

    # Validate PIN before starting
    if not validate_pin(pin):
        print(f"[!] Invalid PIN in config ({pin!r}). Generating a new secure PIN…")
        pin = generate_secure_pin()
        cfg["pin"] = pin
        save_config(cfg)
        print(f"    New PIN: {pin}")

    print("[*] Starting DropSync Pro Engine in-process…")

    import app as backend_app

    server = backend_app.run_in_process(port)
    server_thread = threading.Thread(target=server.run, daemon=True, name="dropsync-server")
    server_thread.start()

    # Wait up to 5 s for server to respond
    for _ in range(20):
        time.sleep(0.25)
        if _is_server_up(port):
            break
    else:
        print("[!] Server did not respond in 5 seconds — check for port conflicts.")
        server.should_exit = True
        return

    _write_state(port)
    print(f"[✓] DropSync Pro started")
    print(f"    Local:  http://localhost:{port}")
    print(f"    LAN:    http://{get_lan_ips()[0]}:{port}")
    print(f"    PIN:    {pin}")
    print("    Press Ctrl+C to stop.")

    try:
        server_thread.join()
    except KeyboardInterrupt:
        print("\n[*] Stopping…")
        server.should_exit = True
        server_thread.join(timeout=3)
        _clear_state()
        print("[✓] Stopped.")


def cmd_stop():
    port = _read_state()
    if port and _is_server_up(port):
        result = _api("/api/engine/shutdown", port, method="POST")
        time.sleep(0.5)
        if not _is_server_up(port):
            _clear_state()
            print("[✓] DropSync Pro stopped.")
            return
    # Fallback: nothing to stop
    _clear_state()
    print("[-] DropSync Pro is not running.")


def cmd_restart():
    cmd_stop()
    time.sleep(1)
    cmd_start()


def cmd_status():
    cfg = load_config()
    port = cfg.get("port", 8080)
    pin = cfg.get("pin", "")

    if not _is_server_up(port):
        print("Status: 🔴 STOPPED")
        print(f"    Run: dropsync start")
        return

    print("Status: 🟢 RUNNING")
    print(f"    Local:  http://localhost:{port}")
    for ip in get_lan_ips():
        print(f"    LAN:    http://{ip}:{port}")
    print(f"    PIN:    {pin}")

    data = _api("/api/engine/monitor", port)
    if "_error" not in data:
        devs = len(data.get("connected_devices", []))
        uptime = data.get("uptime", 0)
        h, r = divmod(uptime, 3600)
        m, s = divmod(r, 60)
        print(f"    Uptime: {h:02d}:{m:02d}:{s:02d}")
        print(f"    Devices: {devs}")


def cmd_pin(args):
    cfg = load_config()
    if args and args[0] == "reset":
        new_pin = generate_secure_pin()
        cfg["pin"] = new_pin
        save_config(cfg)
        print(f"[✓] New PIN: {new_pin}")
        print("    Restart the server to apply: dropsync restart")
    else:
        print(f"Current PIN: {cfg.get('pin', 'Not set')}")


def cmd_devices():
    cfg = load_config()
    port = cfg.get("port", 8080)
    data = _api("/api/engine/monitor", port)
    if "_error" in data:
        print("[!] Server not running or unreachable.")
        return
    devs = data.get("connected_devices", [])
    print(f"Connected Devices ({len(devs)}):")
    for d in devs:
        status = "[BLOCKED]" if d.get("blocked") else "[ACTIVE]"
        print(f"  {d.get('name')} | {d.get('ip')} | {status} | Last: {d.get('lastSeen')}")


def cmd_logs():
    cfg = load_config()
    port = cfg.get("port", 8080)
    data = _api("/api/engine/monitor", port)
    if "_error" in data:
        print("[!] Server not running or unreachable.")
        return
    logs = data.get("activity_logs", [])
    print(f"Recent Audit Log ({len(logs)} entries):")
    for entry in logs[:20]:
        print(f"  [{entry.get('time')}] [{entry.get('type','?').upper():8s}] {entry.get('message')}")


def cmd_qr():
    cfg = load_config()
    port = cfg.get("port", 8080)
    data = _api("/api/status", port)
    if "_error" in data:
        print("[!] Server not running. Start with: dropsync start")
        return
    print(f"Scan this URL on your phone: {data.get('primaryUrl')}")
    print("(Or open the DropSync Pro Control Panel → Phone QR Code tab)")


def cmd_open():
    cfg = load_config()
    port = cfg.get("port", 8080)
    webbrowser.open(f"http://localhost:{port}")


def cmd_version():
    print("DropSync Pro v2.0.0 — LAN File Transfer & Clipboard Hub")
    print("  Architecture: FastAPI + uvicorn in-process, CustomTkinter GUI")
    print("  Repo: https://github.com/AbhijeetRON/DropSync-Pro")


USAGE = """\
DropSync Pro CLI
================
  dropsync start       Start server (foreground, Ctrl+C to stop)
  dropsync stop        Stop the running server
  dropsync restart     Stop then start
  dropsync status      Show status, LAN URLs, uptime, device count
  dropsync pin         Show current access PIN
  dropsync pin reset   Generate a new random 6-digit PIN
  dropsync devices     List authenticated connected devices
  dropsync logs        Show recent security + transfer log
  dropsync qr          Show phone pairing URL
  dropsync open        Open web dashboard in browser
  dropsync version     Show version info
"""

def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return

    cmd = sys.argv[1].lower()
    extra = sys.argv[2:]

    match cmd:
        case "start":    cmd_start()
        case "stop":     cmd_stop()
        case "restart":  cmd_restart()
        case "status":   cmd_status()
        case "pin":      cmd_pin(extra)
        case "devices":  cmd_devices()
        case "logs":     cmd_logs()
        case "qr":       cmd_qr()
        case "open":     cmd_open()
        case "version":  cmd_version()
        case _:
            print(f"Unknown command: {cmd!r}\n")
            print(USAGE)
            sys.exit(1)

if __name__ == "__main__":
    main()
