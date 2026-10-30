"""End-to-end smoke test in MOCK mode (no keys, no network):  python3 -m unittest -v"""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request

os.environ.update(PAYPAL_CLIENT_ID="", PAYPAL_CLIENT_SECRET="", AI_API_KEY="", SETTLE_ENV_FILE="/nonexistent",
                  DB_PATH=os.path.join(tempfile.mkdtemp(), "t.db"), PORT="8799")
from settle import server  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

BASE = "http://127.0.0.1:8799"


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class Smoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.db.conn()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 8799), server.H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        time.sleep(0.2)

    def test_1_seed_and_guardrails(self):
        st, r = call("/api/seed", {})
        self.assertEqual(st, 200)
        cases = {c["id"]: c for c in call("/api/cases")[1]}
        by_cat = {c["proposal"]["category"]: c for c in cases.values()}
        self.assertEqual(by_cat["damaged"]["status"], "refunded")            # 24 EUR -> autopilot
        self.assertEqual(by_cat["damaged"]["proposal"]["language"], "es")
        self.assertEqual(by_cat["wrong_item"]["proposal"]["amount"], 9.6)    # 20% partial
        injected = by_cat["not_as_expected"]
        self.assertEqual(injected["proposal"]["action"], "decline")          # prompt injection ignored
        self.assertEqual(injected["status"], "replied")

    def test_2_shop_flow_needs_approval(self):
        st, o = call("/api/orders", {"cart": {"VASE": 1}})
        self.assertEqual(st, 200)
        st, cap = call(f"/api/orders/{o['id']}/capture", {"payer": {"email": "x@example.com", "name": "X"}})
        self.assertEqual(cap["status"], "COMPLETED")
        st, m = call("/api/messages", {"email": "x@example.com", "order_ref": cap["ref"], "text": "The vase arrived cracked"})
        self.assertEqual(m["status"], "pending_approval")                   # 65 > 30 auto limit
        st, too_much = call(f"/api/cases/{m['case_id']}/approve", {"amount": 999})
        self.assertEqual(st, 400)                                            # guardrail: > refundable
        st, c = call(f"/api/cases/{m['case_id']}/approve", {"amount": 65})
        self.assertEqual((st, c["status"]), (200, "refunded"))              # merchant one-click approval

    def test_3_shop_flow_ok(self):
        _, o = call("/api/orders", {"cart": {"BOWLS": 1}})
        _, cap = call(f"/api/orders/{o['id']}/capture", {"payer": {"email": "y@example.com", "name": "Y"}})
        _, m = call("/api/messages", {"email": "y@example.com", "order_ref": cap["ref"], "text": "Both bowls arrived broken!"})
        self.assertEqual(m["status"], "pending_approval")
        st, c = call(f"/api/cases/{m['case_id']}/approve", {})
        self.assertEqual((st, c["status"]), (200, "refunded"))
        self.assertTrue(c["refund"]["id"].startswith("MOCKREF-"))
        self.assertEqual(c["order"]["refunded"], 48.0)


if __name__ == "__main__":
    unittest.main()
