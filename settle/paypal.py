"""Minimal PayPal REST client (Orders v2 + Payments v2) for the SANDBOX.

If no credentials are configured the client runs in MOCK mode and returns
responses shaped like the real API, so the whole product can be demoed offline.
"""
import base64
import json
import time
import urllib.error
import urllib.request
import uuid

from . import config

_token = {"value": None, "exp": 0}


class PayPalError(Exception):
    def __init__(self, status, body):
        super().__init__(f"PayPal API error {status}: {body}")
        self.status, self.body = status, body


def _token_value():
    if _token["value"] and time.time() < _token["exp"] - 60:
        return _token["value"]
    creds = base64.b64encode(f"{config.PAYPAL_CLIENT_ID}:{config.PAYPAL_CLIENT_SECRET}".encode()).decode()
    req = urllib.request.Request(
        config.PAYPAL_BASE_URL + "/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        headers={"Authorization": "Basic " + creds, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    _token.update(value=data["access_token"], exp=time.time() + int(data.get("expires_in", 3000)))
    return _token["value"]


def _call(method, path, body=None, request_id=None):
    headers = {"Authorization": "Bearer " + _token_value(), "Content-Type": "application/json",
               "Prefer": "return=representation"}
    if request_id:
        headers["PayPal-Request-Id"] = request_id  # idempotency: retries never double-refund
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(config.PAYPAL_BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise PayPalError(e.code, e.read().decode("utf-8", "replace")[:800])


def _money(v):
    return f"{float(v):.2f}"


# ---------------------------------------------------------------- Orders v2
def create_order(ref, items, currency):
    total = sum(i["price"] * i["qty"] for i in items)
    if config.MOCK_PAYPAL:
        return {"id": "MOCK-" + uuid.uuid4().hex[:12].upper(), "status": "CREATED"}
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": ref,
            "invoice_id": ref,
            "description": "Taller Luna handmade ceramics",
            "amount": {"currency_code": currency, "value": _money(total),
                       "breakdown": {"item_total": {"currency_code": currency, "value": _money(total)}}},
            "items": [{"name": i["name"], "quantity": str(i["qty"]), "category": "PHYSICAL_GOODS",
                       "unit_amount": {"currency_code": currency, "value": _money(i["price"])}} for i in items],
        }],
    }
    return _call("POST", "/v2/checkout/orders", body, request_id="create-" + ref)


def capture_order(order_id, payer=None):
    if config.MOCK_PAYPAL:
        payer = payer or {}
        return {
            "id": order_id, "status": "COMPLETED",
            "payer": {"email_address": payer.get("email", "buyer@example.com"),
                      "name": {"given_name": payer.get("name", "Sandbox"), "surname": "Buyer"}},
            "purchase_units": [{"payments": {"captures": [
                {"id": "MOCKCAP-" + uuid.uuid4().hex[:10].upper(), "status": "COMPLETED"}]}}],
        }
    return _call("POST", f"/v2/checkout/orders/{order_id}/capture", {}, request_id="capture-" + order_id)


def get_order(order_id):
    if config.MOCK_PAYPAL or order_id.startswith("MOCK-"):
        return {"id": order_id, "status": "COMPLETED", "mock": True}
    return _call("GET", f"/v2/checkout/orders/{order_id}")


# ---------------------------------------------------------------- Payments v2
def get_capture(capture_id):
    if config.MOCK_PAYPAL or capture_id.startswith("MOCKCAP-"):
        return {"id": capture_id, "status": "COMPLETED", "mock": True}
    return _call("GET", f"/v2/payments/captures/{capture_id}")


def refund_capture(capture_id, amount, currency, note, request_id, invoice_id=None):
    if config.MOCK_PAYPAL or capture_id.startswith("MOCKCAP-"):
        return {"id": "MOCKREF-" + uuid.uuid4().hex[:10].upper(), "status": "COMPLETED",
                "amount": {"currency_code": currency, "value": _money(amount)}, "mock": True}
    body = {"amount": {"currency_code": currency, "value": _money(amount)}, "note_to_payer": note[:255]}
    if invoice_id:
        body["invoice_id"] = invoice_id
    return _call("POST", f"/v2/payments/captures/{capture_id}/refund", body, request_id=request_id)


def capture_details(capture_result):
    """Extract capture id + payer info from an Orders v2 capture response."""
    cap = capture_result["purchase_units"][0]["payments"]["captures"][0]
    payer = capture_result.get("payer", {})
    name = " ".join(filter(None, [payer.get("name", {}).get("given_name"), payer.get("name", {}).get("surname")]))
    return cap["id"], cap.get("status"), payer.get("email_address", ""), name
