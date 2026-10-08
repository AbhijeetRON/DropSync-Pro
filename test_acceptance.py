import unittest
import urllib.request
import urllib.error
import json
import time
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class DropSyncAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server engine
        cls.proc = subprocess.Popen([sys.executable, str(BASE_DIR / "app.py")], cwd=str(BASE_DIR))
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        if cls.proc:
            cls.proc.terminate()
            cls.proc.wait()

    def test_01_health_check(self):
        req = urllib.request.Request("http://127.0.0.1:8080/api/status")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            self.assertEqual(resp.status, 200)
            self.assertTrue("primaryUrl" in data)

    def test_02_brute_force_pin_lockout(self):
        url = "http://127.0.0.1:8080/api/auth/login"
        bad_payload = json.dumps({"pin": "000000"}).encode("utf-8")
        
        # 5 consecutive failures
        for i in range(5):
            req = urllib.request.Request(url, data=bad_payload, headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req)
            except urllib.error.HTTPError as e:
                self.assertIn(e.code, [401, 429])

        # 6th attempt must be 429 Locked out
        req = urllib.request.Request(url, data=bad_payload, headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 429)

if __name__ == "__main__":
    unittest.main()
