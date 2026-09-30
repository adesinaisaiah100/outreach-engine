# 🤖 LinkedIn Outreach Engine

A fully automated, AI-powered LinkedIn outreach tool that runs locally on your own machine using your own LinkedIn account and Chrome browser. No cloud, no subscriptions — just your laptop.

---

## 📋 Table of Contents

1. [How It Works](#how-it-works)
2. [What You Need Before Starting](#what-you-need-before-starting)
3. [Step 1 — One-Time Setup](#step-1--one-time-setup)
4. [Step 2 — Configure Your Identity](#step-2--configure-your-identity)
5. [Step 3 — Connect Your LinkedIn Chrome Profile](#step-3--connect-your-linkedin-chrome-profile)
6. [Step 4 — Prepare Your Leads File](#step-4--prepare-your-leads-file)
7. [Step 5 — Launch & Run](#step-5--launch--run)
8. [Understanding the Dashboard](#understanding-the-dashboard)
9. [Safety & LinkedIn Ban Prevention](#safety--linkedin-ban-prevention)
10. [Message Customization](#message-customization)
11. [Troubleshooting](#troubleshooting)

---

## How It Works

```
Your Leads File (Excel/CSV)
        │
        ▼
┌───────────────────┐
│  AI Auto-Normalizer│  ← Detects names, roles, LinkedIn URLs from any messy file
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Gemini AI Engine │  ← Classifies gender, Nigerian names, HR vs Candidate persona
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Your Chrome      │  ← Opens real LinkedIn profiles using YOUR logged-in account
│  (LinkedIn)       │
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
[1st degree] [2nd/3rd degree]
Send DM      Send Connection Request + Note
    │         │
    └────┬────┘
         ▼
  Excel updated with
  status after each profile
```

**Key principle:** Everything runs on YOUR computer, using YOUR LinkedIn session and YOUR residential IP address. This makes it virtually undetectable by LinkedIn's bot detection.

---

## What You Need Before Starting

| Requirement | Details |
|---|---|
| **Windows PC** | Windows 10 or 11 |
| **Python 3.10+** | Free at [python.org](https://python.org) — check "Add to PATH" during install |
| **Google Chrome** | Must be installed at the default location |
| **LinkedIn Account** | Your real account — logged in via Chrome |
| **Gemini API Key** | Free at [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| **Leads File** | Excel (.xlsx) or CSV with names + LinkedIn URLs |

---

## Step 1 — One-Time Setup

> ⚠️ You only do this ONCE. After this, you just double-click `START_DASHBOARD.bat` every time.

1. Download or unzip the `corecv_outreach` folder anywhere on your PC (e.g. your Desktop).
2. Double-click **`SETUP.bat`**.
3. Wait for it to finish (it installs Python packages and downloads the Chrome browser driver — about 1-2 minutes).
4. At the end, it will **automatically open a file called `.env` in Notepad** for you to fill in.

---

## Step 2 — Configure Your Identity

When Notepad opens your `.env` file, fill in the following values:

```env
# Your Google Gemini API Key (free at aistudio.google.com)
GEMINI_API_KEY=AIzaSy...your_key_here...

# Your first name — used in message signatures
SENDER_NAME=Chidi

# The product or thing you are promoting
PRODUCT_NAME=MyStartup

# One sentence: what you/your product does (for HR messages)
PRODUCT_INTRO=building a hiring intelligence platform that helps companies find the right candidates faster

# One sentence: value to candidates (for Candidate messages)
CANDIDATE_VALUE_PROP=helping professionals build credibility and unlock better job opportunities
```

**Save and close Notepad when done.**

> 🔒 Your `.env` file stays on YOUR computer only. Never share it with anyone.

---

## Step 3 — Connect Your LinkedIn Chrome Profile

This is the most important step. The bot controls YOUR real Chrome browser — so you need to make sure Chrome already has your LinkedIn account logged in.

### 3A — Log Into LinkedIn in Chrome (if not already)

1. Open **Google Chrome** normally.
2. Go to [linkedin.com](https://www.linkedin.com) and **log in with your account**.
3. Make sure you stay logged in (tick "Keep me logged in").
4. **Close Chrome completely** before running the bot.

### 3B — How the Bot Connects to Chrome

When you click **Start Campaign** in the dashboard, the bot:

1. **Kills any open Chrome windows** (so there are no conflicts).
2. **Relaunches Chrome** with a special debug port (`--remote-debugging-port=9223`).
3. Uses a dedicated Chrome profile folder saved at:
   ```
   C:\Users\YourName\chrome_automation\
   ```
   This folder stores your LinkedIn login session so you only need to log in once.

### 3C — First Time: Log Into LinkedIn in the Bot's Chrome Window

The **very first time** you run the campaign, the bot will open a new Chrome window. You will see LinkedIn's login page.

**Do this:**
1. Log into your LinkedIn account in that Chrome window.
2. Stop the campaign immediately (click **Stop** in the dashboard).
3. Close the Chrome window.
4. The next time you start, Chrome will remember your session automatically.

> ✅ After the first login, you never need to log in again unless LinkedIn signs you out.

---

## Step 4 — Prepare Your Leads File

The tool accepts **any Excel (.xlsx) or CSV file** — even messy exports from Apollo, LinkedIn, Phantombuster, or scrapers.

### Required columns (the AI will auto-detect them):

| Column | What to include |
|---|---|
| **Name** or **First Name** | Person's full name or first name |
| **LinkedIn URL** | Full profile URL (e.g. `https://www.linkedin.com/in/username`) |
| **Position** / **Title** / **Role** | Their job title |

### Optional but useful:
- **Last Name**
- **Company**
- **Location**

> 💡 Don't worry about messy headers or extra columns. The AI normalizer handles it.

---

## Step 5 — Launch & Run

1. Double-click **`START_DASHBOARD.bat`**.
2. Your browser opens automatically to `http://127.0.0.1:8000`.
3. **Drag and drop** your Excel/CSV leads file onto the upload zone.
4. Review the preview table to confirm names and URLs look correct.
5. Set your campaign options:
   - **Daily Limit**: How many profiles to contact per session (recommended: 30–50).
   - **Target Mode**: All leads / HR only / Candidates only.
   - **Delay**: Time between profiles (recommended: 45–120 seconds).
6. Click **Launch Campaign**.
7. Watch the live log stream to see what's happening in real time.
8. Click **Download Updated Excel** at any time to save your progress.

> ⚠️ **Do not close the black terminal window** while a campaign is running. That window IS the server.

---

## Understanding the Dashboard

| Status Code | Meaning |
|---|---|
| `Pending` | Not yet contacted — will be picked up next run |
| `Contacted` | Successfully sent a message or connection request |
| `Invalid URL` | LinkedIn URL was missing or broken — skip |
| `Skipped: Non-Nigerian` | AI classified this lead as outside target demographic |
| `Failed: No Action Buttons` | Could not find Message or Connect button on their profile |
| `Failed: Connect requires email` | LinkedIn asked for email verification to send connection |
| `Error` | Unexpected error — will retry next run |

---

## Safety & LinkedIn Ban Prevention

The engine has several built-in safety systems:

- ✅ **Runs on your residential IP** — not a datacenter. LinkedIn rarely flags these.
- ✅ **Randomized delays** between profiles (default 45–120 seconds).
- ✅ **Daily limits** — never exceeds your configured cap per session.
- ✅ **Pending detection** — skips leads where an invitation was already sent.
- ✅ **Existing conversation detection** — skips leads you've already messaged.
- ✅ **Connectivity error recovery** — marks leads as `Pending` (not Failed) on network errors so they retry.

### ⚠️ Recommended safe limits:

| Activity | Safe Daily Limit |
|---|---|
| Connection requests | Max 20–25/day (LinkedIn's soft limit) |
| Direct messages | Max 30–50/day |
| Mixed (the default) | Max 40/day total |

---

## Message Customization

Messages are automatically built from your `.env` file. Here's what each message looks like:

### For HR / Recruiters (Direct Message):
```
Hello Mr Chidi,
My name is [SENDER_NAME] and I am [PRODUCT_INTRO].
We are currently trying to understand how recruiters and hiring managers
actually evaluate candidates beyond the resume before we ship the product.
Your perspective as someone who hires candidates would be genuinely helpful.
I would really appreciate 15 minutes of your time to learn from your experience.
Thank you very much.
```

### For HR / Recruiters (Connection Note, max 300 chars):
```
Hello Mr Chidi,
My name is [SENDER_NAME], [PRODUCT_INTRO]. We're researching how recruiters
evaluate candidates beyond resumes before we ship.
Your hiring perspective would be invaluable — would appreciate 15 mins to learn from you.
Thank you very much.
```

### For Candidates (Direct Message):
```
Hi Amaka,
I noticed your background as a Software Engineer and thought you might find this
interesting. We're [CANDIDATE_VALUE_PROP].
We're currently inviting founding users before we launch publicly, and I think
you'd be a great fit.
```

To customize beyond the `.env` variables, edit the `get_candidate_message()` and `get_hr_message()` functions in `outreach.py`.

---

## Troubleshooting

### ❌ "GEMINI_API_KEY is not set"
- Open your `.env` file (it's in the same folder as `START_DASHBOARD.bat`).
- Make sure `GEMINI_API_KEY=` has your actual key after the `=` sign.
- Get a free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

### ❌ "Chrome failed to start with CDP"
- Make sure **Google Chrome** is installed at:
  `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Close all Chrome windows before starting the campaign.

### ❌ LinkedIn keeps asking me to log in
- The first time, log in through the bot's Chrome window (see Step 3C above).
- If it keeps happening, check that `C:\Users\YourName\chrome_automation\` folder exists and is not being deleted.

### ❌ "No pending leads remaining"
- All leads in your file have been processed.
- Upload a new leads file using the drag-and-drop zone.

### ❌ Dashboard won't open / port 8000 already in use
- The `START_DASHBOARD.bat` automatically frees port 8000.
- If it still fails, open Task Manager → find any `python.exe` processes → End Task → try again.

### ❌ Messages are sending but with wrong name/product
- Open your `.env` file and check `SENDER_NAME` and `PRODUCT_NAME` are correct.
- Restart the dashboard after editing `.env`.

---

## File Structure

```
corecv_outreach/
├── 📄 .env.example         ← Copy this to .env and fill in your info
├── 📄 .env                 ← YOUR personal config (never share this)
├── 🚀 START_DASHBOARD.bat  ← Double-click to start (use this every time)
├── ⚙️  SETUP.bat            ← Double-click once to install everything
├── 🐍 server.py            ← The web dashboard backend
├── 🤖 outreach.py          ← The LinkedIn automation engine
├── 📦 importer.py          ← AI-powered leads file normalizer
├── 🎯 action_dispatcher.py ← Smart LinkedIn profile button detector
├── 📋 requirements.txt     ← Python package list (auto-installed by SETUP.bat)
└── 📁 data/                ← Your leads data lives here (auto-created)
    └── active_leads.xlsx   ← Live ledger updated after every profile
```

---

## Quick Reference

```
First time?  →  SETUP.bat  →  fill .env  →  START_DASHBOARD.bat
Every time?  →  START_DASHBOARD.bat  →  upload file  →  Launch Campaign
```
