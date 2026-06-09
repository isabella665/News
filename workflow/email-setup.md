# Email Setup Guide

Two GitHub Actions send emails automatically:
- **Daily** (weekdays, 7am): morning scan checklist
- **Weekly** (Monday, 7am): check-in prep with that week's flagged items

## Step 1 — Create a Gmail App Password

The workflow uses Gmail as a sending account (can be a dedicated one, e.g. `newsworkflow@gmail.com`).

1. Go to your Google Account → Security → 2-Step Verification (must be on)
2. Go to **App passwords** → create one named "News Workflow"
3. Copy the 16-character password

## Step 2 — Add GitHub Secrets

Go to: **github.com/isabella665/news → Settings → Secrets and variables → Actions → New repository secret**

Add these three secrets:

| Secret name | Value |
|-------------|-------|
| `MAIL_USERNAME` | The Gmail address sending the emails (e.g. `newsworkflow@gmail.com`) |
| `MAIL_PASSWORD` | The App Password from Step 1 |
| `RECIPIENT_EMAIL` | Where you want to receive them (e.g. `isabella@seismic.org`) |

## Step 3 — Adjust the Send Time

In `.github/workflows/daily-scan-email.yml` and `weekly-review-email.yml`, change the cron line:

```
- cron: '0 12 * * *'   # 12:00 UTC = 7am EST / 10pm AEST
```

Common offsets from UTC:
- EST (UTC-5): use `0 12` for 7am
- PST (UTC-8): use `0 15` for 7am
- GMT (UTC+0): use `0 7` for 7am
- CET (UTC+1): use `0 6` for 7am

## Step 4 — Test It

Go to **github.com/isabella665/news → Actions → Daily Morning Scan Email → Run workflow** to trigger a test send immediately.

## How the Weekly Email Pulls Flagged Items

The weekly email automatically includes any `ideas-bank/YYYY-MM-DD-flags.md` files created in the past 7 days. So keeping up the daily flagging habit means Monday's email arrives pre-populated.
