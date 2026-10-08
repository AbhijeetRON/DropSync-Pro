import sys
import os
import subprocess
import threading
import time
import socket
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# Determine project paths
BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

server_process = None
is_running = False

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class DropSyncController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DropSync Pro — Engine Monitor")
        self.geometry("450x540")
        self.resizable(False, False)
        self.configure(bg="#0f172a")

        # Configure modern colors
        self.c_bg = "#0f172a"
        self.c_card = "#1e293b"
        self.c_card_border = "#334155"
        self.c_blue = "#0A84FF"
        self.c_blue_hover = "#0071E3"
        self.c_green = "#22c55e"
        self.c_red = "#ef4444"
        self.c_text = "#f8fafc"
        self.c_subtext = "#94a3b8"

        self.lan_ip = get_lan_ip()
        self.port = 8080

        self.create_widgets()
        self.check_status_loop()

    def create_widgets(self):
        # Header Container
        header_frame = tk.Frame(self, bg=self.c_bg, padx=20, pady=18)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            header_frame, 
            text="⚡ DropSync Pro", 
            font=("Segoe UI", 16, "bold"), 
            fg=self.c_text, 
            bg=self.c_bg
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame, 
            text="Desktop Engine Monitor & Server Controller", 
            font=("Segoe UI", 9), 
            fg=self.c_subtext, 
            bg=self.c_bg
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Main Status Card
        card = tk.Frame(self, bg=self.c_card, highlightbackground=self.c_card_border, highlightthickness=1, padx=20, pady=18)
        card.pack(fill=tk.X, padx=20, pady=5)

        # Status row
        status_row = tk.Frame(card, bg=self.c_card)
        status_row.pack(fill=tk.X, pady=(0, 12))

        tk.Label(status_row, text="ENGINE STATUS", font=("Segoe UI", 8, "bold"), fg=self.c_subtext, bg=self.c_card).pack(side=tk.LEFT)
        self.status_pill = tk.Label(
            status_row, 
            text="● STOPPED", 
            font=("Segoe UI", 9, "bold"), 
            fg=self.c_red, 
            bg="#450a0a",
            padx=10, 
            pady=3
        )
        self.status_pill.pack(side=tk.RIGHT)

        # Divider
        tk.Frame(card, bg=self.c_card_border, height=1).pack(fill=tk.X, pady=6)

        # Network Info
        self.info_frame = tk.Frame(card, bg=self.c_card)
        self.info_frame.pack(fill=tk.X, pady=4)

        self.create_info_row(self.info_frame, "Local Host URL", f"http://localhost:{self.port}", 0)
        self.create_info_row(self.info_frame, "Network LAN IP", f"http://{self.lan_ip}:{self.port}", 1)
        self.create_info_row(self.info_frame, "Security Access PIN", "1234 (Default)", 2)

        # Control Buttons Area
        btn_frame = tk.Frame(self, bg=self.c_bg, padx=20, pady=12)
        btn_frame.pack(fill=tk.X)

        self.toggle_btn = tk.Button(
            btn_frame,
            text="START SERVER",
            font=("Segoe UI", 11, "bold"),
            bg=self.c_blue,
            fg="white",
            activebackground=self.c_blue_hover,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            pady=10,
            command=self.toggle_server
        )
        self.toggle_btn.pack(fill=tk.X, pady=(0, 8))

        action_row = tk.Frame(btn_frame, bg=self.c_bg)
        action_row.pack(fill=tk.X)

        self.open_browser_btn = tk.Button(
            action_row,
            text="🌐 Open in Browser",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="white",
            activebackground="#475569",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            pady=7,
            command=self.open_browser
        )
        self.open_browser_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.open_folder_btn = tk.Button(
            action_row,
            text="📁 Shared Files",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="white",
            activebackground="#475569",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            pady=7,
            command=self.open_shared_folder
        )
        self.open_folder_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        # Real-time Server Log Console
        log_frame = tk.Frame(self, bg=self.c_bg, padx=20, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(log_frame, text="ACTIVITY LOG", font=("Segoe UI", 8, "bold"), fg=self.c_subtext, bg=self.c_bg).pack(anchor="w", pady=(0, 4))

        self.log_text = tk.Text(
            log_frame,
            bg="#020617",
            fg="#cbd5e1",
            font=("Consolas", 8),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#1e293b",
            padx=10,
            pady=8,
            height=7
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.insert(tk.END, "DropSync Pro Engine Initialized.\nReady to start.\n")
        self.log_text.configure(state=tk.DISABLED)

    def create_info_row(self, parent, label, value, row_idx):
        r = tk.Frame(parent, bg=self.c_card)
        r.pack(fill=tk.X, pady=3)
        tk.Label(r, text=label, font=("Segoe UI", 8), fg=self.c_subtext, bg=self.c_card).pack(side=tk.LEFT)
        tk.Label(r, text=value, font=("Consolas", 8, "bold"), fg=self.c_text, bg=self.c_card).pack(side=tk.RIGHT)

    def log(self, message):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def toggle_server(self):
        global is_running, server_process
        if not is_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        global is_running, server_process
        try:
            cmd = [PYTHON_EXE, str(BASE_DIR / "app.py")]
            # Start process without popups
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            server_process = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=startupinfo,
                text=True,
                bufsize=1
            )
            is_running = True
            self.status_pill.configure(text="● RUNNING", fg="#22c55e", bg="#052e16")
            self.toggle_btn.configure(text="STOP SERVER", bg=self.c_red, activebackground="#dc2626")
            self.log(f"Server started on port {self.port}")
            self.log(f"Access LAN at http://{self.lan_ip}:{self.port}")

            # Pipe logs asynchronously
            threading.Thread(target=self.stream_process_logs, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")

    def stream_process_logs(self):
        global server_process, is_running
        if server_process and server_process.stdout:
            for line in iter(server_process.stdout.readline, ''):
                if line:
                    clean = line.strip()
                    if "Uvicorn running" in clean or "200 OK" in clean or "POST" in clean or "GET" in clean:
                        self.log(clean)
            server_process.stdout.close()

    def stop_server(self):
        global is_running, server_process
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=2)
            except Exception:
                server_process.kill()
            server_process = None

        is_running = False
        self.status_pill.configure(text="● STOPPED", fg=self.c_red, bg="#450a0a")
        self.toggle_btn.configure(text="START SERVER", bg=self.c_blue, activebackground=self.c_blue_hover)
        self.log("Server stopped successfully.")

    def open_browser(self):
        webbrowser.open(f"http://localhost:{self.port}")

    def open_shared_folder(self):
        folder = BASE_DIR / "shared_data"
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            os.startfile(folder)
        else:
            subprocess.run(["xdg-open", str(folder)])

    def check_status_loop(self):
        global is_running, server_process
        if server_process and server_process.poll() is not None:
            # Unexpected exit
            if is_running:
                self.stop_server()
                self.log("Server process terminated.")
        self.after(1000, self.check_status_loop)

if __name__ == "__main__":
    app = DropSyncController()
    # Auto clean up on exit
    def on_closing():
        global server_process
        if server_process:
            try:
                server_process.terminate()
            except Exception:
                pass
        app.destroy()
    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()
