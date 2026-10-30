import os


def load_env(path=".env"):
    """Tiny .env loader (no dependencies). Existing env vars win."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env(os.environ.get("SETTLE_ENV_FILE", ".env"))


def env(name, default=""):
    return os.environ.get(name, default) or default


PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = env("PAYPAL_CLIENT_SECRET")
PAYPAL_BASE_URL = env("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
CURRENCY = env("CURRENCY", "EUR")
AI_BASE_URL = env("AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
AI_API_KEY = env("AI_API_KEY")
AI_MODEL = env("AI_MODEL", "gemini-2.5-flash")
HOST = env("HOST", "127.0.0.1")
PORT = int(env("PORT", "8787"))
CONSOLE_PASSWORD = env("CONSOLE_PASSWORD")
DB_PATH = env("DB_PATH", "settle.db")

if "sandbox" not in PAYPAL_BASE_URL:
    raise SystemExit("Settle refuses to run against live PayPal. Use the sandbox base URL.")

MOCK_PAYPAL = not (PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)
RULES_AI = not AI_API_KEY
