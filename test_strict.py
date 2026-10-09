import unittest
import urllib.request
import urllib.error
import json
import time
import threading
from pathlib import Path

from config_manager import load_config, validate_pin, save_config
import app as backend_app

class DropSyncStrictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        # Guarantee valid 6-digit PIN
        cls.pin = cls.config["pin"]
        cls.port = 8089
        cls.server = backend_app.run_in_process(cls.port)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        time.sleep(1.5)

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.should_exit = True
            time.sleep(0.5)

    def test_01_status_and_health(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/status")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            self.assertEqual(resp.status, 200)
            self.assertTrue(data["requirePin"])

    def test_02_empty_and_invalid_pin_rejected(self):
        url = f"http://127.0.0.1:{self.port}/api/auth/login"
        for bad_pin in ["", "123", "abc123", "0000000"]:
            payload = json.dumps({"pin": bad_pin}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req)
            self.assertIn(ctx.exception.code, [401, 429])

    def test_03_successful_authentication_and_device_tracking(self):
        url = f"http://127.0.0.1:{self.port}/api/auth/login"
        payload = json.dumps({"pin": self.pin}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            self.assertEqual(data.get("status"), "ok")

        # Verify device appears in engine monitor
        mon_req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/engine/monitor")
        with urllib.request.urlopen(mon_req) as resp:
            mon_data = json.loads(resp.read().decode())
            devs = mon_data.get("connected_devices", [])
            self.assertTrue(any(d.get("name") == "Apple iPhone" for d in devs))

    def test_04_stream_upload_download(self):
        # Authenticate first to get cookie
        login_url = f"http://127.0.0.1:{self.port}/api/auth/login"
        login_payload = json.dumps({"pin": self.pin}).encode("utf-8")
        login_req = urllib.request.Request(login_url, data=login_payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(login_req)
        cookie = resp.headers.get("Set-Cookie").split(";")[0]

        # Multipart upload
        boundary = "----DropSyncBoundary12345"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="test_stream.bin"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
            f"DROP_SYNC_TEST_DATA_STREAM\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        up_req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/upload",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Cookie": cookie
            }
        )
        with urllib.request.urlopen(up_req) as up_resp:
            self.assertEqual(up_resp.status, 200)

        # Download and verify content
        down_req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/download/test_stream.bin",
            headers={"Cookie": cookie}
        )
        with urllib.request.urlopen(down_req) as down_resp:
            self.assertEqual(down_resp.read(), b"DROP_SYNC_TEST_DATA_STREAM")

if __name__ == "__main__":
    unittest.main()
