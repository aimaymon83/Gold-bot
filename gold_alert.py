"""
Gold Volatility Alert
---------------------
Watches spot gold (XAU/USD) and emails you when the price has moved by a
large amount (default: $20 or more) within the last 10 minutes.

Pulls 1-minute candles from Twelve Data (free tier), measures both the
net move (close now vs close 10 minutes ago) and the full high-low range
of the window, and alerts if either exceeds the threshold.

Includes a cooldown so a sustained volatile stretch doesn't email you
every 10 minutes.

Designed to be run on a schedule (GitHub Actions / cron) — see README.md.
Not financial advice. Educational / personal-use tool only.
"""

import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

# ---------- CONFIG ----------
TWELVE_DATA_API_KEY = os.environ["TWELVE_DATA_API_KEY"]

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
ALERT_TO = os.environ.get("ALERT_TO", SMTP_USER)

SYMBOL = os.environ.get("GOLD_SYMBOL", "XAU/USD")
THRESHOLD_USD = float(os.environ.get("GOLD_THRESHOLD_USD", "20"))
WINDOW_MINUTES = int(os.environ.get("GOLD_WINDOW_MINUTES", "10"))
COOLDOWN_MINUTES = int(os.environ.get("ALERT_COOLDOWN_MINUTES", "30"))

STATE_FILE = os.path.join(os.path.dirname(__file__), "gold_state.json")


# ---------- DATA ----------

def fetch_candles():
    """Last WINDOW_MINUTES+2 one-minute candles, chronological order."""
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": "1min",
        "outputsize": WINDOW_MINUTES + 2,
        "apikey": TWELVE_DATA_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    data = resp.json()
    if "values" not in data:
        raise RuntimeError(f"API error — {data.get('message', data)}")
    candles = list(reversed(data["values"]))  # newest-first -> chronological
    return [
        {
            "time": c["datetime"],
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
        }
        for c in candles
    ]


# ---------- STATE ----------

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def in_cooldown(state):
    last = state.get("last_alert_utc")
    if not last:
        return False
    last_dt = datetime.fromisoformat(last)
    return datetime.now(timezone.utc) - last_dt < timedelta(minutes=COOLDOWN_MINUTES)


# ---------- EMAIL ----------

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_TO
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [ALERT_TO], msg.as_string())


# ---------- MAIN ----------

def main():
    state = load_state()

    candles = fetch_candles()
    window = candles[-WINDOW_MINUTES:]
    if len(window) < 2:
        print("Not enough candle data returned — market may be closed.")
        return

    latest_close = window[-1]["close"]
    start_close = window[0]["close"]
    net_move = latest_close - start_close

    window_high = max(c["high"] for c in window)
    window_low = min(c["low"] for c in window)
    full_range = window_high - window_low

    print(
        f"{SYMBOL} | latest={latest_close:.2f} | "
        f"net {WINDOW_MINUTES}min move={net_move:+.2f} | "
        f"high-low range={full_range:.2f} | threshold={THRESHOLD_USD:.2f}"
    )

    triggered = abs(net_move) >= THRESHOLD_USD or full_range >= THRESHOLD_USD

    if not triggered:
        print("No large fluctuation — no email.")
        return

    if in_cooldown(state):
        print(f"Fluctuation detected but within {COOLDOWN_MINUTES}min cooldown — no email.")
        return

    direction = "UP" if net_move > 0 else "DOWN" if net_move < 0 else "VOLATILE (range spike)"
    subject = f"GOLD ALERT: {SYMBOL} moved {net_move:+.2f} USD in {WINDOW_MINUTES} min ({direction})"
    body = (
        f"Large gold fluctuation detected.\n\n"
        f"Symbol:        {SYMBOL}\n"
        f"Window:        last {WINDOW_MINUTES} minutes\n"
        f"Net move:      {net_move:+.2f} USD\n"
        f"High-low range:{full_range:.2f} USD  (high {window_high:.2f} / low {window_low:.2f})\n"
        f"Latest price:  {latest_close:.2f} USD\n"
        f"Window start:  {window[0]['time']} (price {start_close:.2f})\n"
        f"Checked at:    {datetime.now(timezone.utc).isoformat()} UTC\n\n"
        f"Next alert suppressed for {COOLDOWN_MINUTES} minutes to avoid spam.\n\n"
        f"(Educational tool only — not financial advice.)"
    )
    send_email(subject, body)
    print(f"Email sent: {subject}")

    state["last_alert_utc"] = datetime.now(timezone.utc).isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
