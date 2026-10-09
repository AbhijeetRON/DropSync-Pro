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
- Includes Start Menu integration, desktop shortcut, optional startup with Windows, uninstaller, and `dropsync` CLI in your PATH.
- *Does not require Python or command line knowledge.*

### 2. Docker (Servers & Linux Workstations)
Run DropSync Pro in a hardened container with read-only rootfs and persistent `/data` volume:

```bash
# Start in background
docker compose up -d

# View live transfer logs and generated PIN
docker compose logs -f

# Read your generated PIN from the container volume
docker compose exec dropsync cat /data/config.json

# Stop server
docker compose down
```

### 3. From Source
If running directly from Python source:
```bash
git clone https://github.com/AbhijeetRON/DropSync-Pro.git
cd DropSync-Pro
pip install -r requirements.txt
python controller.py
```

---

## Terminal CLI Reference

Once installed, use the unified `dropsync` command from any terminal:

```bash
# Start the background server engine
dropsync start

# Check engine state, LAN URLs, and connected devices
dropsync status

# List active devices (phones, tablets, PCs)
dropsync devices

# View or regenerate random 6-digit PIN
dropsync pin
dropsync pin reset

# View live security and transfer audit logs
dropsync logs

# Open web portal in default browser
dropsync open

# Stop server engine
dropsync stop
```

---

## Security Notice

> **Important**: DropSync Pro is built for trusted local area networks (LANs). **Do not expose DropSync Pro directly to the public internet.**

- **Random 6-Digit PIN**: Generated on first launch; there are no default credentials.
- **Brute-Force Rate Limiting**: 5 consecutive incorrect PIN entries triggers a 15-minute IP lockout.
- **Path Isolation**: Directory traversal (`../`) is blocked; only files inside the designated shared vault can be accessed.
- **Non-Root Docker**: Containers drop all Linux capabilities (`cap_drop: [ALL]`), enable `read_only: true`, and run as unprivileged user `10001`.

---

## Troubleshooting & FAQ

### Phone cannot connect to the PC?
1. **Private Network Firewall**: Click **"Configure Firewall"** in the control panel to allow incoming TCP connections on private networks.
2. **Same Wi-Fi Network**: Ensure both phone and PC are connected to the same Wi-Fi SSID. If your router has "AP Isolation" or "Client Isolation" enabled, devices cannot communicate.
3. **Virtual Machines**: When running DropSync Pro inside a VM, change the Network Adapter from **NAT** to **Bridged Adapter** so the VM receives an IP on your physical router subnet.

---

## License

DropSync Pro is licensed under the [MIT License](LICENSE).
