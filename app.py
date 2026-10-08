import os
import sys
import socket
import secrets
import shutil
import mimetypes
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import (
    FastAPI,
    Request,
    Response,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    WebSocket,
    WebSocketDisconnect
)
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import qrcode
import io
import base64

# Base setup
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "shared_data"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Configurations
SECURITY_PIN = os.getenv("SHARE_PIN", "1234")  # Default PIN 1234, can be customized or disabled
REQUIRE_PIN = os.getenv("REQUIRE_PIN", "true").lower() in ("true", "1", "yes")
PORT = int(os.getenv("PORT", "8080"))

app = FastAPI(title="DropSync Pro - Secure Local File & Stream Sharing")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for live shared links, commands, and snippets
shared_items = []
connected_websockets: List[WebSocket] = []

def get_local_ip_addresses() -> List[str]:
    """Retrieve all available IPv4 LAN addresses."""
    ips = []
    try:
        # Preferred method to find outbound IP
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

def generate_qr_base64(url: str) -> str:
    """Generate high-contrast QR code as data URI."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

# Security token verifier
AUTH_TOKEN = secrets.token_hex(16)
active_sessions = set()

def verify_session(request: Request) -> bool:
    if not REQUIRE_PIN:
        return True
    auth_cookie = request.cookies.get("dropsync_session")
    auth_header = request.headers.get("x-auth-pin")
    if auth_cookie in active_sessions or auth_header == SECURITY_PIN:
        return True
    return False

async def broadcast_event(event_type: str, data: dict):
    message = json.dumps({"type": event_type, "data": data})
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Heartbeat / ping handling
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
    except Exception:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

@app.get("/api/status")
async def get_system_status(request: Request):
    ips = get_local_ip_addresses()
    urls = [f"http://{ip}:{PORT}" for ip in ips]
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
        "pin": SECURITY_PIN if not REQUIRE_PIN else "****"
    }

@app.post("/api/auth/login")
async def login(data: dict, response: Response):
    pin = str(data.get("pin", "")).strip()
    if not REQUIRE_PIN or pin == SECURITY_PIN:
        session_id = secrets.token_hex(24)
        active_sessions.add(session_id)
        response.set_cookie(
            key="dropsync_session",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=86400 * 7
        )
        return {"status": "ok", "message": "Authenticated"}
    raise HTTPException(status_code=401, detail="Invalid Security PIN")

@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    session_id = request.cookies.get("dropsync_session")
    if session_id in active_sessions:
        active_sessions.remove(session_id)
    response.delete_cookie("dropsync_session")
    return {"status": "ok"}

# Endpoints for links, commands, clipboard, and snippets
@app.get("/api/items")
async def list_items(request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"items": shared_items}

@app.post("/api/items")
async def add_item(data: dict, request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    item_type = data.get("type", "text") # text, link, command, code
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
    # Put newest first
    shared_items.insert(0, new_item)
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

# File Sharing Endpoints
@app.get("/api/files")
async def list_files(request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    files = []
    for p in STORAGE_DIR.glob("**/*"):
        if p.is_file():
            stat = p.stat()
            rel_path = str(p.relative_to(STORAGE_DIR)).replace("\\", "/")
            mime, _ = mimetypes.guess_type(p.name)
            is_image = mime and mime.startswith("image/")
            is_video = mime and mime.startswith("video/")
            is_audio = mime and mime.startswith("audio/")

            files.append({
                "name": p.name,
                "path": rel_path,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p"),
                "mime": mime or "application/octet-stream",
                "isImage": bool(is_image),
                "isVideo": bool(is_video),
                "isAudio": bool(is_audio),
            })
    # Sort files newest first
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

    uploaded = []
    target_dir = STORAGE_DIR
    if subfolder:
        clean_sub = Path(subfolder).resolve()
        if str(clean_sub).startswith(str(STORAGE_DIR.resolve())):
            target_dir = clean_sub
            target_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        safe_filename = Path(file.filename).name
        destination = target_dir / safe_filename
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        stat = destination.stat()
        mime, _ = mimetypes.guess_type(safe_filename)
        info = {
            "name": safe_filename,
            "path": str(destination.relative_to(STORAGE_DIR)).replace("\\", "/"),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p"),
            "mime": mime or "application/octet-stream"
        }
        uploaded.append(info)

    await broadcast_event("files_uploaded", {"count": len(uploaded), "files": uploaded})
    return {"status": "ok", "uploaded": uploaded}

@app.get("/api/download/{file_path:path}")
async def download_file(file_path: str, request: Request):
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    file_p = (STORAGE_DIR / file_path).resolve()
    if not str(file_p).startswith(str(STORAGE_DIR.resolve())) or not file_p.is_file():
        raise HTTPException(status_code=404, detail="File not found")

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
    if not str(file_p).startswith(str(STORAGE_DIR.resolve())) or not file_p.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    file_p.unlink()
    await broadcast_event("file_deleted", {"path": file_path})
    return {"status": "ok"}

# Serve frontend single page app
@app.get("/")
async def serve_index():
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>DropSync Pro is loading...</h1>")

# Mount static files if directory exists
static_path = BASE_DIR / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

if __name__ == "__main__":
    print(f"==================================================")
    print(f"   DROPSYNC PRO - CROSS-DEVICE LOCAL SHARE")
    print(f"==================================================")
    ips = get_local_ip_addresses()
    for ip in ips:
        print(f" -> Local LAN Portal:  http://{ip}:{PORT}")
    print(f" -> Security PIN:       {SECURITY_PIN}")
    print(f" -> Storage Directory:  {STORAGE_DIR}")
    print(f"==================================================")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
