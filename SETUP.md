# Auto Data Update — Setup Guide

The script `update_data.py` downloads the latest CSVs from Google Drive and pushes to GitHub.
Windows Task Scheduler runs it at **10:30 AM** and **3:00 PM** IST every day.

---

## Step 1 — Install Python dependencies

Open a terminal in the project folder and run:

```
pip install -r requirements.txt
```

---

## Step 2 — Create Google Drive API credentials

1. Go to https://console.cloud.google.com/
2. Create a project (or select existing)
3. Enable **Google Drive API**
4. Go to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth client ID**
6. Application type: **Desktop app** → name it anything → Create
7. Download the JSON → save it as `credentials.json` in this folder

---

## Step 3 — Authorize (first run only)

Run the script once manually from the terminal:

```
python update_data.py
```

A browser window will open asking you to sign in with your Google account
(selvakumar.s@scootsy.com) and grant Drive read access.
A `token.json` file will be saved — the script uses it for all future runs.

---

## Step 4 — Confirm git remote is set

```
git remote -v
```

Should show `origin https://github.com/2018285/rca-bucket-trend-dashboard.git`

If not:
```
git remote add origin https://github.com/2018285/rca-bucket-trend-dashboard.git
```

Make sure you are authenticated (Personal Access Token or GitHub CLI):
```
gh auth login
```

---

## Step 5 — Register Task Scheduler tasks

Open **Command Prompt as Administrator** and run:

```
schtasks /Create /XML "C:\Users\selvakumar.s\Documents\RCA Bucket Trend\task_1030am.xml" /TN "RCA Dashboard Update 10:30AM" /F
schtasks /Create /XML "C:\Users\selvakumar.s\Documents\RCA Bucket Trend\task_300pm.xml"  /TN "RCA Dashboard Update 3:00PM"  /F
```

To verify they are registered:
```
schtasks /Query /TN "RCA Dashboard Update 10:30AM"
schtasks /Query /TN "RCA Dashboard Update 3:00PM"
```

To run immediately for testing:
```
schtasks /Run /TN "RCA Dashboard Update 10:30AM"
```

---

## What the script does each run

1. Connects to Google Drive folder `1dWSFOJK_hAMDlIcxGHH8RPihTqhd7OIf`
2. Finds the latest version of each CSV (by modified date)
3. Downloads and overwrites the local CSV files
4. Runs `git add -A` → `git commit` → `git push origin master`
5. Live dashboard updates at: https://2018285.github.io/rca-bucket-trend-dashboard/dashboard.html

All activity is logged to `update_log.txt` in this folder.

---

## Drive file → Local file mapping

| Drive file name (contains)       | Local file                                                 |
|----------------------------------|------------------------------------------------------------|
| Item_level_daily                 | IGCC-RCA-Appsheet Summary - Item_level_daily.csv           |
| Item_level_weekly                | IGCC-RCA-Appsheet Summary - Item_level_weekly.csv          |
| Spoc_level (D-2)                 | IGCC-RCA-Appsheet Summary - Spoc_level (D-2).csv           |
| Spoc_level (not D-2)             | IGCC-RCA-Appsheet Summary - Spoc_level.csv                 |
| Daily-RCA-Summary                | Weekly RCA bucket sumarry - Daily-RCA-Summary.csv          |
| WeeklyRCA-Summary                | Weekly RCA bucket sumarry - WeeklyRCA-Summary (2).csv      |
| City List                        | Weekly RCA bucket sumarry - City List.csv                  |
