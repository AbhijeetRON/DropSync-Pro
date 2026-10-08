# DropSync Pro

**Peer-to-peer local network file transfer, media streaming, and live clipboard hub with Apple Liquid Glass design.**

DropSync Pro connects your Windows PC, Mac, iPhone, Android, and Linux devices over your local Wi-Fi or LAN with gigabit speeds, PIN authentication, and zero third-party cloud dependencies.

<div align="center">
  <img src="preview.png" alt="DropSync Pro Interface" width="850" />
</div>

---

## 3-Step Quick Start

1. **Download**: Grab `DropSyncPro-Setup.exe` from [GitHub Releases](https://github.com/AbhijeetRON/DropSync-Pro/releases).
2. **Install**: Run the installer (takes under 30 seconds; no Python or runtime required).
3. **Scan QR**: Launch DropSync Pro, click **Connect Device**, and scan the QR code with your phone.

---

## Installation Options

### 1. Windows Installer (Recommended)
Download and run the standalone installer:
- **[Download DropSyncPro-Setup.exe](https://github.com/AbhijeetRON/DropSync-Pro/releases)**
- Includes Start Menu integration, desktop shortcut, optional startup with Windows, and uninstaller.
- *Does not require Python or command line knowledge.*

### 2. Docker (Servers & Linux Workstations)
Run DropSync Pro in a hardened, non-root container:

```bash
# Start in background
docker compose up -d

# View live transfer logs
docker compose logs -f

# Stop server
docker compose down
```

### 3. From Source
If you prefer running from Python source:
```bash
git clone https://github.com/AbhijeetRON/DropSync-Pro.git
cd DropSync-Pro
pip install -r requirements.txt
python app.py
```

---

## CLI Reference

DropSync Pro includes a unified terminal command tool (`dropsync`):

```bash
# Start the background server engine
py dropsync_cli.py start

# Check engine state, LAN URLs, and connected devices
py dropsync_cli.py status

# List active devices (phones, tablets, PCs)
py dropsync_cli.py devices

# View or regenerate random 6-digit PIN
py dropsync_cli.py pin
py dropsync_cli.py pin reset

# View live security and transfer audit logs
py dropsync_cli.py logs

# Open web portal in default browser
py dropsync_cli.py open

# Stop server engine
py dropsync_cli.py stop
```

---

## Security Notice

> **Important**: DropSync Pro is built for trusted local area networks (LANs). **Do not expose DropSync Pro directly to the public internet.**

- **Random PIN**: A random 6-digit PIN is generated on first launch; there are no default credentials.
- **Brute-Force Rate Limiting**: 5 consecutive incorrect PIN entries triggers a 15-minute IP lockout.
- **Path Isolation**: Directory traversal (`../`) is blocked; only files inside the designated shared vault can be accessed.
- **Non-Root Docker**: Containers drop all Linux capabilities (`cap_drop: [ALL]`) and run as an unprivileged user.

---

## Troubleshooting & FAQ

### Phone cannot connect to the PC?
1. **Private Network Firewall**: On first run, click **"Allow Firewall Rule"** in the control panel, or ensure Windows Firewall allows TCP incoming traffic on port 8080 for Private networks.
2. **Same Wi-Fi Network**: Ensure both phone and PC are connected to the same Wi-Fi SSID. If your router has "AP Isolation" or "Client Isolation" enabled, devices cannot communicate.
3. **Virtual Machines**: When running DropSync Pro inside a VM (VirtualBox, VMware), change the Network Adapter from **NAT** to **Bridged Adapter** so the VM receives an IP on your physical router subnet.

---

## License

DropSync Pro is licensed under the [MIT License](LICENSE).
