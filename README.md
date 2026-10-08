# DropSync Pro ⚡

> **High-speed, peer-to-peer local network transfer hub for files, media, live clipboard & terminal commands with Apple Liquid Glass UI.**

DropSync Pro is a self-hosted cross-device transfer system designed for Windows, macOS, Linux, and mobile devices (iOS & Android). It lets you transfer gigabyte-sized files, paste clipboard snippets, and broadcast commands over your local Wi-Fi/LAN without relying on third-party servers.

---

## ✨ Features

- ⚡ **High-Speed Direct LAN Transfer**: No speed limits, zero cloud storage bottlenecks.
- 📱 **QR Code Mobile Pairing**: Instant connection for phones and tablets on the same Wi-Fi.
- 📋 **Live Shared Clipboard & Commands**: Share code blocks, terminal commands, and links with 1-click copy.
- 🎨 **Apple Liquid Glass Design**: macOS Tahoe/iOS inspired frosted-glass UI with real background blur and smooth interactions.
- 🔒 **PIN-Protected Security**: PIN/token authentication prevents unauthorized devices on your network from accessing data.
- 🐳 **Docker & 1-Click Launch**: Run natively on Windows with `run.bat` or via Docker Compose.

---

## 🚀 Quick Start

### 1. Windows (1-Click)
Double-click `run.bat` or run:
```bash
pip install -r requirements.txt
python app.py
```
Open **`http://localhost:8080`** in your browser.

### 2. Docker
```bash
docker compose up -d --build
```

---

## 🔒 Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Port DropSync listens on |
| `REQUIRE_PIN` | `true` | Enable/disable PIN protection |
| `SHARE_PIN` | `1234` | Security PIN required for access |

---

## 📄 License
MIT License
