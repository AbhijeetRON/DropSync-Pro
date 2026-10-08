import os
import json
import secrets
from pathlib import Path

CONFIG_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "DropSyncPro"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "port": 8080,
    "require_pin": True,
    "pin": "",  # Will be generated as random 6-digit PIN on first run
    "shared_dir": str(Path.home() / "DropSync_Shared"),
    "use_https": False,
    "max_upload_size_mb": 2048,  # 2 GB default
    "auto_delete_hours": 0,      # 0 = disabled
    "start_with_windows": False,
    "theme": "light",
    "rate_limit_attempts": 5,
    "lockout_minutes": 15
}

def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        cfg = DEFAULT_CONFIG.copy()
        cfg["pin"] = f"{secrets.randbelow(900000) + 100000}"  # Secure 6-digit PIN
        save_config(cfg)
        return cfg
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        if not data.get("pin"):
            data["pin"] = f"{secrets.randbelow(900000) + 100000}"
            save_config(data)
        return data
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
