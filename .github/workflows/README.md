# Gold Volatility Alert Bot

Emails you whenever spot gold (XAU/USD) moves **$20 or more within 10
minutes** — either as a net move (price now vs 10 minutes ago) or as a
high-low range spike inside the window.

Includes a 30-minute cooldown after each alert so a volatile session
doesn't flood your inbox.

Not financial advice. Educational tool for your own monitoring.

## Setup (same pattern as the FX bot)

### 1. Free Twelve Data API key
https://twelvedata.com — free tier covers XAU/USD 1-minute candles.
Usage here: 1 API call per check × 6 checks/hour = ~144/day, well inside
the 800/day free limit.

### 2. Gmail App Password
2-Step Verification on → https://myaccount.google.com/apppasswords →
generate a Mail password, copy the 16-character code.

### 3. GitHub repo — make it PUBLIC (important, see below)
Upload all files keeping the `.github/workflows/` folder structure.

**Why public?** GitHub Actions gives *unlimited* minutes on public repos
but only 2,000/month on private ones. Running every 10 minutes ≈ 4,300
runner-minutes/month — over the private-repo cap. On a public repo it's
free without limit. Your API key and email password are stored in GitHub
**Secrets**, which are never visible in a public repo — only this code is.
If you'd rather keep the repo private, change the cron to every 30 min
(`"*/30 * * * *"`) to stay under the free cap.

### 4. Add secrets
Repo → Settings → Secrets and variables → Actions:

| Secret | Value |
|---|---|
| `TWELVE_DATA_API_KEY` | your Twelve Data key |
| `SMTP_USER` | your Gmail address |
| `SMTP_PASSWORD` | 16-char app password |
| `ALERT_TO` | destination email |

### 5. Test
Actions tab → "Gold Volatility Alert" → Run workflow. The log shows the
current 10-min move and range. To force a test email, temporarily set
`GOLD_THRESHOLD_USD: "0.1"` in the workflow file, run it once, then set
it back to `"20"`.

## Tuning

All knobs are env vars in `.github/workflows/gold-alert.yml`:

- `GOLD_THRESHOLD_USD` — alert threshold in dollars (default 20)
- `GOLD_WINDOW_MINUTES` — lookback window (default 10)
- `ALERT_COOLDOWN_MINUTES` — quiet period after an alert (default 30)
- `GOLD_SYMBOL` — swap to another metal/pair Twelve Data supports
  (e.g. `XAG/USD` for silver)

## Honest limitations

- **Detection lag**: the check runs every 10 minutes and GitHub's free
  scheduler can drift a few extra minutes, so you'll typically learn of a
  spike 5–15 minutes after it happens — fine for awareness, not for
  reacting within seconds. Sub-minute alerting needs an always-on process
  (a $4/month VPS, or your own machine running the script in a loop).
- **Market hours**: gold trades ~23/5. Outside trading hours the API
  returns stale candles and nothing will trigger — expected behavior.
- A $20/10-min move in gold is a genuinely big event (news releases, Fed
  announcements) — at this threshold expect alerts on eventful days, not
  daily.
