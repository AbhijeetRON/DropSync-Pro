<div align="center">

  # ⚡ DropSync Pro
  ### Next-Gen Cross-Device Local Transfer & Live Clipboard Hub

  <p align="center">
    <b>High-Speed P2P LAN Transfer • Apple Liquid Glass UI • Instant QR Pairing • Zero Cloud Dependencies</b>
  </p>

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
  [![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
  [![Cross Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20iOS%20%7C%20Android-4A154B?style=for-the-badge)](#-system-requirements)

  <br />

  <img src="preview.png" alt="DropSync Pro Liquid Glass UI" width="900" style="border-radius: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.15);" />

</div>

---

## ⚡ Super Easy One-Line Install (No Git Required!)

Anyone can install and run DropSync Pro immediately without installing Git or cloning repos manually.

### 🪟 Windows (PowerShell One-Liner):
Press `Win + X` -> Open **PowerShell** or **Terminal**, paste this command and press Enter:

```powershell
irm https://raw.githubusercontent.com/AbhijeetRON/DropSync-Pro/main/install.ps1 | iex
```
> **What this does:** Automatically downloads DropSync Pro, installs dependencies, places a shortcut on your Desktop, and launches the Engine Controller GUI!

---

## 🎛️ Desktop Engine Monitor & GUI Controller

DropSync Pro comes with a built-in Desktop Controller app to monitor, start, and stop the server with one click.

- **Start / Stop Server**: Instant toggle without leaving terminal windows open.
- **Engine Status Pill**: Shows `RUNNING` or `STOPPED` in real-time.
- **Network Link**: One-click **"Open in Browser"** and **"Shared Files Folder"**.
- **Activity Log**: Watch live HTTP requests, transfers, and uploads.

**To open the GUI Controller:**
- Double-click **`dropsync.bat`** in the folder, or
- Run in terminal:
  ```bash
  py cli.py gui
  ```

---

## 💻 Terminal & Command-Line Control (CLI)

Prefer using the command line? DropSync Pro includes a full CLI manager:

```bash
# Start server in the background
py cli.py start

# Check engine status and view active LAN IP addresses
py cli.py status

# Stop background server
py cli.py stop

# Restart server
py cli.py restart

# Open Desktop GUI Monitor
py cli.py gui
```

---

## 🌟 Key Features

- 🚀 **Gigabit LAN Speeds**: Direct device-to-device transfers over Wi-Fi without cloud throttles.
- 🎨 **Apple Liquid Glass Design**: macOS Tahoe / iOS inspired translucent UI with real background blur.
- 📱 **QR Code Instant Pairing**: Point your phone camera at the screen to connect immediately.
- 📋 **Live Multi-Device Clipboard**: Copy text or commands on your PC; paste them immediately on your phone (and vice-versa).
- 🔒 **PIN-Protected Security**: Keep unauthorized devices on your network locked out.
- 🌐 **100% Private**: Zero external servers, zero telemetry.

---

## 💻 System Requirements

### 🖥️ Host Machine (Where server runs)
| OS | Minimum Version | Runtime Requirement | RAM & Storage |
|---|---|---|---|
| **Windows** | Windows 10 / 11 (64-bit) | Python 3.10+ or Docker | 256 MB RAM, 100 MB disk |
| **macOS** | macOS Monterey or newer (Intel / Apple Silicon) | Python 3.10+ or Docker | 256 MB RAM, 100 MB disk |
| **Linux** | Ubuntu, Debian, Fedora, Arch, Alpine | Python 3.10+ or Docker | 128 MB RAM, 100 MB disk |

### 📱 Client Devices (Connecting to share files)
| Device Type | Supported Systems | Requirements |
|---|---|---|
| **Smartphones** | iOS 14+ (iPhone), Android 8.0+ | Any modern browser (Safari, Chrome, Firefox) |
| **Laptops / Tablets** | iPadOS, ChromeOS, Windows, Mac | Any modern web browser |
| **Network** | Any local Wi-Fi, Ethernet LAN, or Hotspot | Connected to the same network |

---

## 🐳 Docker Deployment

```bash
# Run in container
docker compose up -d --build
```
Access at `http://<your-host-ip>:8080`.

---

## ⚙️ Configuration & Customization

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Port for the web portal |
| `REQUIRE_PIN` | `true` | Set to `false` to disable PIN authentication |
| `SHARE_PIN` | `1234` | Change to any custom password or PIN |

---

## 📄 License
MIT License - Developed with ❤️ by [AbhijeetRON](https://github.com/AbhijeetRON)
