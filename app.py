import os
import sys
import socket
import secrets
import shutil
import mimetypes
import json
import asyncio
import time
import ipaddress
import hmac
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set
from collections import defaultdict
from urllib.parse import urlparse

from fastapi import (
    FastAPI,
    Request,
    Response,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    WebSocket,
    WebSocketDisconnect
)
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import qrcode
import io
import base64

from config_manager import load_config, validate_pin

BASE_DIR = Path(__file__).resolve().parent

# Load configuration and strictly validate PIN
config = load_config()
PIN = str(config.get("pin", "")).strip()
if not validate_pin(PIN):
    raise RuntimeError(f"FATAL: DropSync Pro refused to start. Configured PIN must be a valid 6-digit numeric string. Got: '{PIN}'")

PORT = int(config.get("port", 8080))
REQUIRE_PIN = bool(config.get("require_pin", True))
STORAGE_DIR = Path(config.get("shared_dir")).resolve()
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = int(config.get("max_upload_size_mb", 2048)) * 1024 * 1024
RATE_LIMIT_ATTEMPTS = int(config.get("rate_limit_attempts", 5))
LOCKOUT_SECONDS = int(config.get("lockout_minutes", 15)) * 60

app = FastAPI(title="DropSync Pro Engine", docs_url=None, redoc_url=None)

# In-memory shared items and engine stats
shared_items = []
connected_websockets: List[WebSocket] = []

# Device tracking: ONLY authenticated devices appear
authenticated_devices: Dict[str, dict] = {} # ip -> device metadata
blocked_ips: Set[str] = set()

# Security: Rate limiting & Brute force tracking
failed_attempts: Dict[str, List[float]] = defaultdict(list) # ip -> list of failure timestamps
active_sessions: Dict[str, float] = {} # token -> expiry timestamp

START_TIME = time.time()
engine_stats = {
    "bytes_uploaded": 0,
    "bytes_downloaded": 0,
    "active_transfers": 0
}
activity_logs: List[dict] = []

def add_log(event_type: str, message: str, ip: str = "127.0.0.1"):
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": event_type,
        "message": message,
        "ip": ip
    }
    activity_logs.insert(0, entry)
    if len(activity_logs) > 300:
        activity_logs.pop()

def get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "127.0.0.1"

def is_ip_locked(ip: str) -> bool:
    if ip in blocked_ips:
        return True
    now = time.time()
    # Clean up old timestamps
    failed_attempts[ip] = [t for t in failed_attempts[ip] if now - t < LOCKOUT_SECONDS]
    return len(failed_attempts[ip]) >= RATE_LIMIT_ATTEMPTS

def record_failed_attempt(ip: str):
    failed_attempts[ip].append(time.time())
    attempts = len(failed_attempts[ip])
    remaining = max(0, RATE_LIMIT_ATTEMPTS - attempts)
    add_log("security", f"Failed PIN attempt from {ip} ({remaining} remaining before lockout)", ip)
    if attempts >= RATE_LIMIT_ATTEMPTS:
        add_log("security", f"IP {ip} LOCKED OUT for {LOCKOUT_SECONDS // 60} minutes due to repeated failures", ip)

def get_local_ip_addresses() -> List[str]:
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(('8.8.8.8', 80))
        primary_ip = s.getsockname()[0]
        s.close()
        ips.append(primary_ip)
    except Exception:
        pass

    try:
        host_name = socket.gethostname()
        for ip in socket.gethostbyname_ex(host_name)[2]:
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    if not ips:
        ips.append("127.0.0.1")
    return ips

def parse_user_agent(ua: str) -> str:
    ua_low = ua.lower()
    if "iphone" in ua_low: return "Apple iPhone"
    elif "ipad" in ua_low: return "Apple iPad"
    elif "android" in ua_low: return "Android Device"
    elif "macintosh" in ua_low or "mac os" in ua_low: return "macOS Workstation"
    elif "windows" in ua_low: return "Windows PC"
    elif "linux" in ua_low: return "Linux Workstation"
    return "Web Client"

def generate_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def verify_session(request: Request) -> bool:
    if not REQUIRE_PIN:
        return True
    ip = get_client_ip(request)
    if is_ip_locked(ip):
        return False
    cookie_token = request.cookies.get("dropsync_session")
    if cookie_token and cookie_token in active_sessions:
        if time.time() < active_sessions[cookie_token]:
            return True
        else:
            del active_sessions[cookie_token]
    return False

# Security Middleware: Host Header Validation & Rate-limit Enforcement
@app.middleware("http")
async def security_host_validation(request: Request, call_next):
    host_header = request.headers.get("host", "")
    # Check valid host format (hostname or ip, optional port)
    host_name = host_header.split(":")[0].strip() if host_header else ""
    valid_hosts = {"localhost", "127.0.0.1", "::1"} | set(get_local_ip_addresses())
    
    # Allow local connections
    if host_name and host_name not in valid_hosts:
        # Check if it's a private subnet IP
        try:
            ip_obj = ipaddress.ip_address(host_name)
            if not (ip_obj.is_private or ip_obj.is_loopback):
                return JSONResponse(status_code=400, content={"detail": "Public Host header rejected."})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Host header."})

    response = await call_next(request)
    return response

async def broadcast_event(event_type: str, data: dict):
    msg = json.dumps({"type": event_type, "data": data})
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)

# Auto-delete cleaner
async def auto_cleaner_task():
    while True:
        await asyncio.sleep(300)
        cfg = load_config()
        hours = int(cfg.get("auto_delete_hours", 0))
        if hours > 0:
            threshold = time.time() - (hours * 3600)
            for p in STORAGE_DIR.glob("**/*"):
                if p.is_file() and p.name != ".gitkeep":
                    try:
                        if p.stat().st_mtime < threshold:
                            p.unlink()
                            add_log("system", f"Auto-deleted expired file: {p.name}")
                    except Exception:
                        pass

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auto_cleaner_task())
    add_log("system", f"DropSync Pro Engine started on port {PORT}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    
    # Security: Validate Origin Header
    origin = websocket.headers.get("origin")
    if origin:
        parsed_origin = urlparse(origin)
        origin_host = parsed_origin.hostname
        valid_hosts = {"localhost", "127.0.0.1", "::1"} | set(get_local_ip_addresses())
        if origin_host not in valid_hosts:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    if client_ip in blocked_ips or is_ip_locked(client_ip):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    cookie_token = websocket.cookies.get("dropsync_session")
    if REQUIRE_PIN and (not cookie_token or cookie_token not in active_sessions):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
    except Exception:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

@app.get("/api/status")
async def get_system_status(request: Request):
    ip = get_client_ip(request)
    if is_ip_locked(ip):
        raise HTTPException(status_code=429, detail="IP address temporarily locked out due to multiple failed PIN attempts.")

    ips = get_local_ip_addresses()
    urls = [f"http://{i}:{PORT}" for i in ips]
    primary_url = urls[0] if urls else f"http://localhost:{PORT}"
    qr_data = generate_qr_base64(primary_url)
    is_authenticated = verify_session(request)

    return {
        "authenticated": is_authenticated,
        "requirePin": REQUIRE_PIN,
        "primaryUrl": primary_url,
        "allUrls": urls,
        "qrCode": qr_data,
        "port": PORT,
        "uptimeSeconds": int(time.time() - START_TIME)
    }

@app.post("/api/auth/login")
async def login(data: dict, request: Request, response: Response):
    ip = get_client_ip(request)
    if is_ip_locked(ip):
        raise HTTPException(status_code=429, detail="IP locked out due to repeated failed attempts. Please wait 15 minutes.")

    pin_input = str(data.get("pin", "")).strip()
    
    # Constant-time comparison using hmac.compare_digest
    is_valid_pin = hmac.compare_digest(pin_input.encode("utf-8"), PIN.encode("utf-8"))

    if not REQUIRE_PIN or is_valid_pin:
        # Success: reset failed attempts
        if ip in failed_attempts:
            del failed_attempts[ip]

        session_id = secrets.token_hex(32)
        active_sessions[session_id] = time.time() + (86400 * 7) # 7-day expiry
        response.set_cookie(
            key="dropsync_session",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=86400 * 7
        )

        ua = request.headers.get("user-agent", "Unknown")
        dev_name = parse_user_agent(ua)
        authenticated_devices[ip] = {
            "ip": ip,
            "name": dev_name,
            "userAgent": ua,
            "lastSeen": datetime.now().strftime("%H:%M:%S"),
            "connectedSince": authenticated_devices.get(ip, {}).get("connectedSince", datetime.now().strftime("%H:%M:%S")),
            "blocked": False
        }

        add_log("auth", f"Authenticated: {dev_name} ({ip})", ip)
        return {"status": "ok", "message": "Authenticated"}

    record_failed_attempt(ip)
    raise HTTPException(status_code=401, detail="Invalid Security PIN")

@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    ip = get_client_ip(request)
    token = request.cookies.get("dropsync_session")
    if token in active_sessions:
        del active_sessions[token]
    if ip in authenticated_devices:
        del authenticated_devices[ip]
    response.delete_cookie("dropsync_session")
    return {"status": "ok"}

@app.get("/api/items")
async def list_items(request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"items": shared_items}

@app.post("/api/items")
async def add_item(data: dict, request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    item_type = data.get("type", "text")
    content = data.get("content", "").strip()
    label = data.get("label", "").strip()
    language = data.get("language", "plaintext")

    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    item_id = secrets.token_hex(6)
    timestamp = datetime.now().strftime("%I:%M %p")

    new_item = {
        "id": item_id,
        "type": item_type,
        "content": content,
        "label": label if label else (content[:35] + "..." if len(content) > 35 else content),
        "language": language,
        "timestamp": timestamp,
        "createdAt": datetime.now().isoformat()
    }
    shared_items.insert(0, new_item)
    add_log("system", f"Shared {item_type}: '{new_item['label']}'", get_client_ip(request))
    await broadcast_event("new_item", new_item)
    return new_item

@app.delete("/api/items/{item_id}")
async def delete_item(item_id: str, request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    global shared_items
    shared_items = [it for it in shared_items if it["id"] != item_id]
    await broadcast_event("delete_item", {"id": item_id})
    return {"status": "ok"}

@app.get("/api/files")
async def list_files(request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    files = []
    for p in STORAGE_DIR.glob("**/*"):
        if p.is_file() and p.name != ".gitkeep":
            stat = p.stat()
            rel_path = str(p.relative_to(STORAGE_DIR)).replace("\\", "/")
            mime, _ = mimetypes.guess_type(p.name)
            files.append({
                "name": p.name,
                "path": rel_path,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p"),
                "mime": mime or "application/octet-stream",
                "isImage": bool(mime and mime.startswith("image/")),
                "isVideo": bool(mime and mime.startswith("video/")),
                "isAudio": bool(mime and mime.startswith("audio/")),
            })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files}

@app.post("/api/upload")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    subfolder: Optional[str] = Form("")
):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    ip = get_client_ip(request)
    engine_stats["active_transfers"] += len(files)
    uploaded = []

    target_dir = STORAGE_DIR
    if subfolder:
        clean_sub = (STORAGE_DIR / subfolder).resolve()
        # Strict security using Path.is_relative_to
        if clean_sub.is_relative_to(STORAGE_DIR):
            target_dir = clean_sub
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            raise HTTPException(status_code=400, detail="Invalid target folder directory")

    try:
        for file in files:
            safe_filename = Path(file.filename).name.replace("..", "").replace("/", "").replace("\\", "").strip()
            if not safe_filename:
                safe_filename = f"file_{secrets.token_hex(4)}"

            destination = target_dir / safe_filename
            
            # Security: Never overwrite existing files; generate unique suffix
            if destination.exists():
                stem = destination.stem
                suffix = destination.suffix
                destination = target_dir / f"{stem}_{secrets.token_hex(3)}{suffix}"

            total_bytes = 0
            with destination.open("wb") as buffer:
                while chunk := await file.read(1024 * 1024): # 1 MB streaming chunks
                    total_bytes += len(chunk)
                    if total_bytes > MAX_UPLOAD_SIZE:
                        destination.unlink(missing_ok=True)
                        raise HTTPException(status_code=413, detail="File exceeds maximum allowed upload size.")
                    buffer.write(chunk)
            
            engine_stats["bytes_uploaded"] += total_bytes
            stat = destination.stat()
            mime, _ = mimetypes.guess_type(destination.name)
            uploaded.append({
                "name": destination.name,
                "path": str(destination.relative_to(STORAGE_DIR)).replace("\\", "/"),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p"),
                "mime": mime or "application/octet-stream"
            })
            add_log("upload", f"Uploaded: {destination.name} ({stat.st_size / (1024*1024):.1f} MB) from {ip}", ip)
    finally:
        engine_stats["active_transfers"] = max(0, engine_stats["active_transfers"] - len(files))

    await broadcast_event("files_uploaded", {"count": len(uploaded), "files": uploaded})
    return {"status": "ok", "uploaded": uploaded}

@app.get("/api/download/{file_path:path}")
async def download_file(file_path: str, request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    file_p = (STORAGE_DIR / file_path).resolve()
    # Path traversal validation using is_relative_to
    if not file_p.is_relative_to(STORAGE_DIR) or not file_p.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    size = file_p.stat().st_size
    engine_stats["bytes_downloaded"] += size
    ip = get_client_ip(request)
    add_log("download", f"Downloaded: {file_p.name} ({size / (1024*1024):.1f} MB) by {ip}", ip)

    mime, _ = mimetypes.guess_type(file_p.name)
    return FileResponse(
        path=str(file_p),
        filename=file_p.name,
        media_type=mime or "application/octet-stream"
    )

@app.delete("/api/files/{file_path:path}")
async def delete_file(file_path: str, request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    file_p = (STORAGE_DIR / file_path).resolve()
    if not file_p.is_relative_to(STORAGE_DIR) or not file_p.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    file_p.unlink()
    add_log("system", f"Deleted: {file_p.name}", get_client_ip(request))
    await broadcast_event("file_deleted", {"path": file_path})
    return {"status": "ok"}

# Local Control Panel Telemetry (Localhost only)
@app.get("/api/engine/monitor")
async def get_engine_metrics(request: Request):
    ip = get_client_ip(request)
    if not (ip == "127.0.0.1" or ip == "::1"):
        raise HTTPException(status_code=403, detail="Localhost access only")

    storage_bytes = sum(f.stat().st_size for f in STORAGE_DIR.glob("**/*") if f.is_file())
    qr_data = generate_qr_base64(f"http://{get_local_ip_addresses()[0]}:{PORT}")

    return {
        "uptime": int(time.time() - START_TIME),
        "port": PORT,
        "pin": PIN,
        "lan_ips": get_local_ip_addresses(),
        "bytes_uploaded": engine_stats["bytes_uploaded"],
        "bytes_downloaded": engine_stats["bytes_downloaded"],
        "active_transfers": engine_stats["active_transfers"],
        "storage_used_bytes": storage_bytes,
        "connected_devices": list(authenticated_devices.values()),
        "activity_logs": activity_logs[:50],
        "qrCode": qr_data
    }

@app.post("/api/engine/device/block")
async def block_device(data: dict, request: Request):
    ip = get_client_ip(request)
    if not (ip == "127.0.0.1" or ip == "::1"):
        raise HTTPException(status_code=403, detail="Localhost access only")
    target_ip = data.get("ip")
    if target_ip:
        blocked_ips.add(target_ip)
        if target_ip in authenticated_devices:
            authenticated_devices[target_ip]["blocked"] = True
        add_log("security", f"Device {target_ip} manually blocked by administrator")
    return {"status": "ok"}

@app.post("/api/engine/device/unblock")
async def unblock_device(data: dict, request: Request):
    ip = get_client_ip(request)
    if not (ip == "127.0.0.1" or ip == "::1"):
        raise HTTPException(status_code=403, detail="Localhost access only")
    target_ip = data.get("ip")
    if target_ip in blocked_ips:
        blocked_ips.remove(target_ip)
    if target_ip in failed_attempts:
        del failed_attempts[target_ip]
    if target_ip in authenticated_devices:
        authenticated_devices[target_ip]["blocked"] = False
    add_log("security", f"Device {target_ip} unblocked by administrator")
    return {"status": "ok"}

# Localhost-only graceful shutdown endpoint (used by `dropsync stop`)
_server_ref: "uvicorn.Server | None" = None

@app.post("/api/engine/shutdown")
async def shutdown_engine(request: Request):
    ip = get_client_ip(request)
    if not (ip == "127.0.0.1" or ip == "::1"):
        raise HTTPException(status_code=403, detail="Localhost access only")
    add_log("system", "Graceful shutdown requested via CLI")
    if _server_ref is not None:
        _server_ref.should_exit = True
    return {"status": "ok"}

@app.get("/")
async def serve_index():
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>DropSync Pro is loading...</h1>")

static_path = BASE_DIR / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

def run_in_process(port: int = PORT, log_file: Optional[Path] = None):
    """
    Create and return a uvicorn.Server bound to the given port.
    Registers the server globally so /api/engine/shutdown can signal it.
    Start it by calling server.run() inside a daemon thread.
    Stop it by setting server.should_exit = True.
    log_config=None prevents crash on windowed EXE (no stdout/stderr).
    """
    global _server_ref
    uv_config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_config=None,   # Critical: prevents crash in windowed PyInstaller EXE
        access_log=False
    )
    server = uvicorn.Server(uv_config)
    _server_ref = server
    return server

if __name__ == "__main__":
    server = run_in_process(PORT)
    server.run()
