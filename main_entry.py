import sys
import threading
import multiprocessing
import uvicorn
from controller import ModernDropSyncApp
import app as backend_app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    # Launch GUI
    gui = ModernDropSyncApp()
    gui.mainloop()
