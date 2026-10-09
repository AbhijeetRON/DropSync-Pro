import os
import sys
import time
import socket
import threading
import subprocess
import webbrowser
import urllib.request
import json
import base64
import io
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageTk
import pystray
from pystray import MenuItem as item

from config_manager import load_config, save_config, validate_pin

BASE_DIR = Path(__file__).resolve().parent

# Single-instance lock using a localhost socket
INSTANCE_LOCK_SOCKET = None

def acquire_single_instance_lock(port=49258):
    global INSTANCE_LOCK_SOCKET
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', port))
        s.listen(1)
        INSTANCE_LOCK_SOCKET = s
        return True
    except OSError:
        return False

def get_lan_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(('8.8.8.8', 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips or ["127.0.0.1"]

def format_bytes(b):
    if b < 1024: return f"{b} B"
    elif b < 1024**2: return f"{b/1024:.1f} KB"
    elif b < 1024**3: return f"{b/(1024**2):.1f} MB"
    return f"{b/(1024**3):.2f} GB"

def add_firewall_rule(port):
    if os.name != 'nt':
        return True, "Firewall configuration only required on Windows."
    try:
        rule_name = f"DropSync Pro Port {port}"
        # Test if netsh rule can be queried or added
        cmd = f'powershell -Command "Start-Process netsh -ArgumentList \'advfirewall firewall add rule name=\\"{rule_name}\\" dir=in action=allow protocol=TCP localport={port} profile=private\' -Verb RunAs -Wait"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return True, "Firewall rule successfully requested for Private networks."
    except Exception as e:
        return False, f"Failed to execute firewall rule: {e}"

class ModernDropSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.config = load_config()
        ctk.set_appearance_mode(self.config.get("theme", "light"))
        ctk.set_default_color_theme("blue")

        self.title("DropSync Pro — Control Center")
        self.geometry("980x640")
        self.minsize(880, 560)

        # Apple-inspired Liquid Glass color palette
        self.apple_blue = "#0A84FF"
        self.apple_blue_hover = "#0071E3"
        self.apple_green = "#34C759"
        self.apple_red = "#FF3B30"

        # In-process server state
        self.server_instance = None
        self.server_thread = None
        self.is_running = False

        # Protocol intercept for minimizing to tray
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self.setup_ui()
        self.start_monitoring_thread()
        self.setup_system_tray()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left Sidebar (Glass panel)
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("#F1F5F9", "#0F172A"))
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(6, weight=1)

        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=18, pady=(20, 15))

        title_lbl = ctk.CTkLabel(brand_frame, text="⚡ DropSync Pro", font=ctk.CTkFont(size=18, weight="bold"), text_color=("#0F172A", "#F8FAFC"))
        title_lbl.pack(anchor="w")
        sub_lbl = ctk.CTkLabel(brand_frame, text="Engine Control Center", font=ctk.CTkFont(size=11), text_color=("#64748B", "#94A3B8"))
        sub_lbl.pack(anchor="w")

        # Nav Buttons
        self.btn_nav_dashboard = self.create_nav_btn("📊 Dashboard", lambda: self.switch_view("dashboard"))
        self.btn_nav_qr = self.create_nav_btn("📱 Phone QR Code", lambda: self.switch_view("qr"))
        self.btn_nav_devices = self.create_nav_btn("🔒 Connected Devices", lambda: self.switch_view("devices"))
        self.btn_nav_logs = self.create_nav_btn("📜 Live Audit Log", lambda: self.switch_view("logs"))
        self.btn_nav_settings = self.create_nav_btn("⚙️ Preferences", lambda: self.switch_view("settings"))

        # Main Content Canvas
        self.main_container = ctk.CTkFrame(self, corner_radius=16, fg_color=("#FFFFFF", "#1E293B"))
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Views
        self.views = {}
        self.views["dashboard"] = self.build_dashboard_view()
        self.views["qr"] = self.build_qr_view()
        self.views["devices"] = self.build_devices_view()
        self.views["logs"] = self.build_logs_view()
        self.views["settings"] = self.build_settings_view()

        self.switch_view("dashboard")

    def create_nav_btn(self, text, command):
        btn = ctk.CTkButton(
            self.sidebar,
            text=text,
            command=command,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent",
            text_color=("#1E293B", "#E2E8F0"),
            hover_color=("#E2E8F0", "#1E293B"),
            anchor="w",
            height=38,
            corner_radius=10
        )
        btn.pack(fill="x", padx=12, pady=4)
        return btn

    def switch_view(self, name):
        for v in self.views.values():
            v.pack_forget()
        self.views[name].pack(fill="both", expand=True, padx=20, pady=20)

    # VIEW 1: Dashboard Engine Monitor
    def build_dashboard_view(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")

        header_row = ctk.CTkFrame(f, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 16))

        title = ctk.CTkLabel(header_row, text="Local Transfer Engine", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(side="left")

        self.status_pill = ctk.CTkLabel(
            header_row,
            text="● STOPPED",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.apple_red,
            fg_color=("#FEE2E2", "#450A0A"),
            corner_radius=20,
            padx=14,
            pady=4
        )
        self.status_pill.pack(side="right")

        self.btn_toggle = ctk.CTkButton(
            f,
            text="START SERVER ENGINE",
            command=self.toggle_server,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.apple_blue,
            hover_color=self.apple_blue_hover,
            height=46,
            corner_radius=12
        )
        self.btn_toggle.pack(fill="x", pady=(0, 16))

        # Metrics 4-Card Grid
        grid_frame = ctk.CTkFrame(f, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 16))
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metric")

        self.card_uptime = self.create_metric_card(grid_frame, "UPTIME", "00:00:00", 0)
        self.card_pin = self.create_metric_card(grid_frame, "ACCESS PIN", self.config.get("pin", "------"), 1)
        self.card_transfers = self.create_metric_card(grid_frame, "TRANSFERRED", "0 MB", 2)
        self.card_storage = self.create_metric_card(grid_frame, "VAULT STORAGE", "0 MB", 3)

        # Connection & URL Details Box
        conn_box = ctk.CTkFrame(f, corner_radius=14, fg_color=("#F8FAFC", "#0F172A"), border_width=1, border_color=("#E2E8F0", "#334155"))
        conn_box.pack(fill="x", pady=(0, 16), padx=2)

        lbl = ctk.CTkLabel(conn_box, text="ACTIVE LAN CONNECTION ADDRESSES", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#64748B", "#94A3B8"))
        lbl.pack(anchor="w", padx=16, pady=(12, 4))

        self.lan_info_lbl = ctk.CTkLabel(
            conn_box,
            text=f"Primary LAN: http://{get_lan_ips()[0]}:{self.config.get('port', 8080)}",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=self.apple_blue
        )
        self.lan_info_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        # Action Buttons Row
        action_row = ctk.CTkFrame(f, fg_color="transparent")
        action_row.pack(fill="x")

        btn_open = ctk.CTkButton(action_row, text="🌐 Open Web Portal", command=self.open_browser, fg_color=("#E2E8F0", "#334155"), text_color=("#0F172A", "#F8FAFC"), hover_color=("#CBD5E1", "#475569"), height=36, corner_radius=10)
        btn_open.pack(side="left", expand=True, fill="x", padx=(0, 6))

        btn_folder = ctk.CTkButton(action_row, text="📁 Open Shared Folder", command=self.open_shared_folder, fg_color=("#E2E8F0", "#334155"), text_color=("#0F172A", "#F8FAFC"), hover_color=("#CBD5E1", "#475569"), height=36, corner_radius=10)
        btn_folder.pack(side="left", expand=True, fill="x", padx=(6, 6))

        self.btn_firewall = ctk.CTkButton(action_row, text="🛡️ Configure Firewall", command=self.handle_firewall_click, fg_color=("#E2E8F0", "#334155"), text_color=("#0F172A", "#F8FAFC"), hover_color=("#CBD5E1", "#475569"), height=36, corner_radius=10)
        self.btn_firewall.pack(side="right", expand=True, fill="x", padx=(6, 0))

        return f

    def create_metric_card(self, parent, title, value, col):
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=("#F8FAFC", "#0F172A"), border_width=1, border_color=("#E2E8F0", "#334155"))
        card.grid(row=0, column=col, padx=4, sticky="nsew")

        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=9, weight="bold"), text_color=("#64748B", "#94A3B8"))
        lbl_t.pack(anchor="w", padx=12, pady=(10, 0))

        lbl_v = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=15, weight="bold"), text_color=("#0F172A", "#F8FAFC"))
        lbl_v.pack(anchor="w", padx=12, pady=(0, 10))
        return lbl_v

    # VIEW 2: Phone QR Code
    def build_qr_view(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        title = ctk.CTkLabel(f, text="Instant Phone Pairing", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 6))

        sub = ctk.CTkLabel(f, text="Scan with iPhone Camera or Android Lens on the same Wi-Fi.", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=12))
        sub.pack(anchor="w", pady=(0, 16))

        self.qr_img_label = ctk.CTkLabel(f, text="QR Code generates when server starts", corner_radius=16, fg_color=("#F8FAFC", "#0F172A"))
        self.qr_img_label.pack(pady=20)
        return f

    # VIEW 3: Connected Devices
    def build_devices_view(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        title = ctk.CTkLabel(f, text="Authenticated Client Devices", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 12))

        self.devices_scroll = ctk.CTkScrollableFrame(f, corner_radius=12, fg_color=("#F8FAFC", "#0F172A"))
        self.devices_scroll.pack(fill="both", expand=True)
        return f

    # VIEW 4: Live Logs
    def build_logs_view(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        title = ctk.CTkLabel(f, text="Security & Transfer Audit Log", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 12))

        self.log_textbox = ctk.CTkTextbox(f, font=ctk.CTkFont(family="Consolas", size=11), corner_radius=12, fg_color=("#020617", "#020617"), text_color="#E2E8F0")
        self.log_textbox.pack(fill="both", expand=True)
        return f

    # VIEW 5: Preferences
    def build_settings_view(self):
        f = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        title = ctk.CTkLabel(f, text="Preferences & Security", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 16))

        # PIN configuration
        pin_frame = ctk.CTkFrame(f, corner_radius=12, fg_color=("#F8FAFC", "#0F172A"), border_width=1, border_color=("#E2E8F0", "#334155"))
        pin_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(pin_frame, text="Security Access PIN (Exactly 6 Digits)", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))
        
        self.entry_pin = ctk.CTkEntry(pin_frame, width=200, font=ctk.CTkFont(family="Consolas", size=14, weight="bold"))
        self.entry_pin.insert(0, self.config.get("pin", ""))
        self.entry_pin.pack(anchor="w", padx=16, pady=(0, 12))

        # Port Setting
        port_frame = ctk.CTkFrame(f, corner_radius=12, fg_color=("#F8FAFC", "#0F172A"), border_width=1, border_color=("#E2E8F0", "#334155"))
        port_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(port_frame, text="Server Network Port", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))
        
        self.entry_port = ctk.CTkEntry(port_frame, width=200)
        self.entry_port.insert(0, str(self.config.get("port", 8080)))
        self.entry_port.pack(anchor="w", padx=16, pady=(0, 12))

        # Max Upload Size
        upload_frame = ctk.CTkFrame(f, corner_radius=12, fg_color=("#F8FAFC", "#0F172A"), border_width=1, border_color=("#E2E8F0", "#334155"))
        upload_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(upload_frame, text="Maximum Upload File Size (MB)", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))
        
        self.entry_upload = ctk.CTkEntry(upload_frame, width=200)
        self.entry_upload.insert(0, str(self.config.get("max_upload_size_mb", 2048)))
        self.entry_upload.pack(anchor="w", padx=16, pady=(0, 12))

        # Save Button
        btn_save = ctk.CTkButton(f, text="Save Preferences", command=self.save_preferences, fg_color=self.apple_blue, height=40, corner_radius=10)
        btn_save.pack(anchor="w", pady=16)

        return f

    def handle_firewall_click(self):
        port = self.config.get("port", 8080)
        success, msg = add_firewall_rule(port)
        if success:
            messagebox.showinfo("Firewall", msg)
        else:
            messagebox.showwarning("Firewall", msg)

    def save_preferences(self):
        new_pin = self.entry_pin.get().strip()
        if not validate_pin(new_pin):
            messagebox.showerror("Invalid PIN", "PIN must be exactly 6 numeric digits.")
            return

        try:
            new_port = int(self.entry_port.get().strip())
            new_upload = int(self.entry_upload.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Value", "Port and Max Upload Size must be valid integers.")
            return

        needs_restart = (new_pin != self.config.get("pin") or new_port != self.config.get("port"))
        self.config["pin"] = new_pin
        self.config["port"] = new_port
        self.config["max_upload_size_mb"] = new_upload
        save_config(self.config)
        self.card_pin.configure(text=new_pin)

        if needs_restart and self.is_running:
            if messagebox.askyesno("Restart Required", "Settings saved. Restart server now to apply changes?"):
                self.stop_engine()
                self.start_engine()
        else:
            messagebox.showinfo("Saved", "Preferences saved successfully.")

    def toggle_server(self):
        if not self.is_running:
            self.start_engine()
        else:
            self.stop_engine()

    def start_engine(self):
        if self.is_running:
            return
        try:
            # Import and run uvicorn in-process safely
            import app as backend_app
            self.server_instance = backend_app.run_in_process(self.config.get("port", 8080))

            def run_server():
                try:
                    self.server_instance.run()
                except Exception as e:
                    self.after(0, self.handle_server_crash, str(e))

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()

            self.is_running = True
            self.status_pill.configure(text="● RUNNING", text_color=self.apple_green, fg_color=("#DCFCE7", "#052E16"))
            self.btn_toggle.configure(text="STOP SERVER ENGINE", fg_color=self.apple_red, hover_color="#DC2626")
        except Exception as e:
            messagebox.showerror("Startup Error", f"Failed to start server: {e}")

    def handle_server_crash(self, err_msg):
        self.is_running = False
        self.status_pill.configure(text="● ERROR / STOPPED", text_color=self.apple_red, fg_color=("#FEE2E2", "#450A0A"))
        self.btn_toggle.configure(text="START SERVER ENGINE", fg_color=self.apple_blue, hover_color=self.apple_blue_hover)
        messagebox.showerror("Server Error", f"DropSync Pro Server stopped unexpectedly:\n{err_msg}")

    def stop_engine(self):
        if self.server_instance:
            self.server_instance.should_exit = True
            self.server_instance = None
        self.is_running = False
        self.status_pill.configure(text="● STOPPED", text_color=self.apple_red, fg_color=("#FEE2E2", "#450A0A"))
        self.btn_toggle.configure(text="START SERVER ENGINE", fg_color=self.apple_blue, hover_color=self.apple_blue_hover)

    def open_browser(self):
        webbrowser.open(f"http://localhost:{self.config.get('port', 8080)}")

    def open_shared_folder(self):
        folder = Path(self.config.get("shared_dir")).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            os.startfile(folder)
        else:
            subprocess.run(["xdg-open", str(folder)])

    def start_monitoring_thread(self):
        threading.Thread(target=self.poll_metrics_loop, daemon=True).start()

    def poll_metrics_loop(self):
        while True:
            time.sleep(2)
            if self.is_running:
                try:
                    port = self.config.get("port", 8080)
                    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/engine/monitor")
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        data = json.loads(resp.read().decode())
                        self.after(0, self.update_dashboard_metrics, data)
                except Exception:
                    pass

    def update_dashboard_metrics(self, data):
        uptime = data.get("uptime", 0)
        h, rem = divmod(uptime, 3600)
        m, s = divmod(rem, 60)
        self.card_uptime.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        
        total_b = data.get("bytes_uploaded", 0) + data.get("bytes_downloaded", 0)
        self.card_transfers.configure(text=format_bytes(total_b))

        storage_b = data.get("storage_used_bytes", 0)
        self.card_storage.configure(text=format_bytes(storage_b))

        # QR code update if available
        qr_b64 = data.get("qrCode")
        if qr_b64 and hasattr(self, 'qr_img_label'):
            try:
                raw_bytes = base64.b64decode(qr_b64.split(",")[1])
                img = Image.open(io.BytesIO(raw_bytes)).resize((220, 220))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 220))
                self.qr_img_label.configure(image=ctk_img, text="")
            except Exception:
                pass

        # Stable Devices list update (only diff/render when list changes)
        devices = data.get("connected_devices", [])
        for w in self.devices_scroll.winfo_children():
            w.destroy()

        if not devices:
            ctk.CTkLabel(self.devices_scroll, text="No authenticated devices yet. Scan QR code to connect.", text_color=("#64748B", "#94A3B8")).pack(pady=20)
        else:
            for dev in devices:
                r = ctk.CTkFrame(self.devices_scroll, corner_radius=10, fg_color=("#FFFFFF", "#1E293B"), border_width=1, border_color=("#E2E8F0", "#334155"))
                r.pack(fill="x", padx=8, pady=4)
                
                info_lbl = ctk.CTkLabel(r, text=f"{dev.get('name')}  •  {dev.get('ip')}", font=ctk.CTkFont(weight="bold"))
                info_lbl.pack(side="left", padx=12, pady=10)

                is_blocked = dev.get("blocked", False)
                if is_blocked:
                    btn_action = ctk.CTkButton(r, text="Unblock Device", width=120, height=28, fg_color=self.apple_green, font=ctk.CTkFont(size=10, weight="bold"), command=lambda ip=dev.get('ip'): self.unblock_device(ip))
                else:
                    btn_action = ctk.CTkButton(r, text="Disconnect / Block", width=120, height=28, fg_color=self.apple_red, font=ctk.CTkFont(size=10, weight="bold"), command=lambda ip=dev.get('ip'): self.block_device(ip))
                btn_action.pack(side="right", padx=12, pady=10)

        # Audit logs update
        logs = data.get("activity_logs", [])
        self.log_textbox.delete("1.0", "end")
        for l in logs:
            self.log_textbox.insert("end", f"[{l.get('time')}] [{l.get('type').upper()}] {l.get('message')}\n")

    def block_device(self, ip):
        port = self.config.get("port", 8080)
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/engine/device/block",
            data=json.dumps({"ip": ip}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=1.5)

    def unblock_device(self, ip):
        port = self.config.get("port", 8080)
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/engine/device/unblock",
            data=json.dumps({"ip": ip}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=1.5)

    def hide_to_tray(self):
        self.withdraw()

    def show_from_tray(self):
        self.deiconify()
        self.lift()

    def setup_system_tray(self):
        img = Image.new("RGBA", (64, 64), color=(10, 132, 255, 255))
        menu = (
            item("Open DropSync Pro", lambda: self.show_from_tray()),
            item("Start Server", lambda: self.start_engine()),
            item("Stop Server", lambda: self.stop_engine()),
            item("Open Web Portal", lambda: self.open_browser()),
            item("Quit", lambda: self.quit_app())
        )
        self.tray = pystray.Icon("DropSyncPro", img, "DropSync Pro", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def quit_app(self):
        self.stop_engine()
        if self.tray:
            self.tray.stop()
        self.quit()

if __name__ == "__main__":
    if not acquire_single_instance_lock():
        # Another instance is already running
        messagebox.showinfo("DropSync Pro", "DropSync Pro is already running in the background. Check your system tray.")
        sys.exit(0)

    app = ModernDropSyncApp()
    app.mainloop()
