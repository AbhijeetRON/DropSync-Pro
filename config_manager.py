import os
import json
import secrets
import tempfile
from pathlib import Path

# Config directory can be overridden via DROPSYNC_DATA_DIR
DATA_DIR_ENV = os.getenv("DROPSYNC_DATA_DIR")
if DATA_DIR_ENV:
    CONFIG_DIR = Path(DATA_DIR_ENV).resolve()
else:
    CONFIG_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "DropSyncPro"

CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "port": 8080,
    "require_pin": True,
    "pin": "",  # Auto-generated 6-digit PIN on initialization
    "shared_dir": str(CONFIG_DIR / "shared_data"),
    "max_upload_size_mb": 2048,  # 2 GB default
    "auto_delete_hours": 0,      # 0 = disabled
    "theme": "light",
    "rate_limit_attempts": 5,
    "lockout_minutes": 15
}

def generate_secure_pin() -> str:
    """Generate a cryptographically secure 6-digit numeric PIN."""
    return f"{secrets.randbelow(900000) + 100000}"

def validate_pin(pin: str) -> bool:
    """Validate that the PIN is exactly 6 digits."""
    return bool(pin and isinstance(pin, str) and len(pin) == 6 and pin.isdigit())

def save_config(cfg: dict):
    """Atomically write configuration to disk to prevent partial/corrupt writes."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Validate PIN before saving
    if not validate_pin(str(cfg.get("pin", ""))):
        raise ValueError("Invalid PIN: PIN must be exactly 6 numeric digits.")

    cfg_json = json.dumps(cfg, indent=2, ensure_ascii=False)
    
    # Write to a temp file in the same directory then rename (atomic on POSIX and Windows NTFS)
    temp_file = tempfile.NamedTemporaryFile("w", dir=str(CONFIG_DIR), delete=False, encoding="utf-8")
    try:
        temp_file.write(cfg_json)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        # Atomic replace
        os.replace(temp_file.name, CONFIG_FILE)
    except Exception:
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)
        raise

def load_config() -> dict:
    """Load configuration, applying environment variable overrides and migrations."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = DEFAULT_CONFIG.copy()

    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if k in cfg:
                        cfg[k] = v
        except Exception:
            pass  # Fall back to default structure with fresh secure PIN

    # Ensure valid PIN is always present
    if not validate_pin(str(cfg.get("pin", ""))):
        cfg["pin"] = generate_secure_pin()
        save_config(cfg)

    # Environment variable overrides (Priority: ENV > config.json)
    if os.getenv("PORT"):
        try:
            cfg["port"] = int(os.getenv("PORT"))
        except ValueError:
            pass

    if os.getenv("REQUIRE_PIN"):
        cfg["require_pin"] = os.getenv("REQUIRE_PIN").lower() in ("true", "1", "yes")

    if os.getenv("SHARE_PIN"):
        env_pin = os.getenv("SHARE_PIN").strip()
        if validate_pin(env_pin):
            cfg["pin"] = env_pin

    if DATA_DIR_ENV:
        cfg["shared_dir"] = str(CONFIG_DIR / "shared_data")

    # Ensure shared directory exists
    Path(cfg["shared_dir"]).mkdir(parents=True, exist_ok=True)
    return cfg
