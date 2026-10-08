# Security Policy

DropSync Pro is designed for trusted local network (LAN) data transfers.

## ⚠️ Important Deployment Notice
> **DO NOT EXPOSE DROPSYNC PRO DIRECTLY TO THE PUBLIC INTERNET.**  
> DropSync Pro binds to local private subnet interfaces (e.g. `192.168.x.x`, `10.x.x.x`). It is not intended as a publicly routed cloud service.

---

## 🔒 Security Architecture

1. **Randomized PIN Generation**:
   - First initialization creates a random 6-digit PIN stored in your local user configuration.
   - There are no hardcoded default credentials.

2. **Brute Force & Rate Limiting**:
   - Incoming requests that fail the security PIN 5 consecutive times trigger an immediate 15-minute IP lockout.
   - All authorization events are logged to the audit log.

3. **Session & Cookie Protections**:
   - Authentication sets cryptographic session tokens protected with `HttpOnly`, `SameSite=Lax`, and 7-day expiration.
   - WebSocket connections enforce Origin validation and session verification prior to handshake acceptance.

4. **Filesystem Isolation**:
   - Filenames are sanitized on arrival.
   - Directory traversal (`../`) is blocked; files outside the designated storage directory cannot be accessed or served.
   - Uploaded files are served with non-executable content types.

---

## 🛡️ Reporting Vulnerabilities

If you discover a security issue or vulnerability:
- Please report it directly via GitHub Security Advisories or email the maintainer.
- Please allow up to 48 hours for a triage response before public disclosure.
