# Changelog

All notable changes to **DropSync Pro** are documented in this file.

## [2.0.0] - 2026-10-08

### Added
- **PyInstaller & Inno Setup Packaging**: Fully bundled standalone Windows installer (`DropSyncPro-Setup.exe`). Users no longer need Python installed.
- **Apple Liquid Glass Control Panel**: Modern desktop GUI built with CustomTkinter and Apple design language.
- **System Tray Integration**: Background engine controls (Start, Stop, Open Dashboard, Quit) and minimize-to-tray.
- **Unified `dropsync` CLI**: Terminal command tool for automated server management (`start`, `stop`, `status`, `devices`, `pin`, `logs`).
- **Security Hardening**:
  - Auto-generated random 6-digit PIN on first run (replaces weak default 1234).
  - 5-attempt rate limiter with 15-minute IP lockout.
  - Non-root user, `cap_drop: [ALL]`, and CIS-compliant Docker container.
- **Automated CI/CD**: GitHub Actions workflow (`.github/workflows/release.yml`) for releasing Windows installers and publishing Docker images to GitHub Container Registry.
- **Firewall Integration**: 1-click Windows Firewall rule setup for private LAN networks.

### Fixed
- Fixed Python installer alias trap where Windows Store shortcuts caused launcher failures.
- Fixed plain-text hardcoded default PIN.
- Hardened WebSocket handshake with origin checks and session token verification.
