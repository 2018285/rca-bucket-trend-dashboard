#!/usr/bin/env python3
"""
update_data.py
Copies the latest CSVs from the local 'RCA CSV Files' folder into the project
root (with the names the dashboard expects), then pushes to GitHub.
On any failure, sends an alert email via Gmail to selvakumar.s@scootsy.com.
Scheduled via Windows Task Scheduler at 10:30 AM and 3:00 PM IST daily.
"""

import sys
import shutil
import smtplib
import logging
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR      = Path(__file__).parent
CSV_SOURCE_DIR  = SCRIPT_DIR / 'RCA CSV Files'
LOG_PATH        = SCRIPT_DIR / 'update_log.txt'
DASHBOARD_NAME  = 'RCA Bucket Trend Dashboard'
DASHBOARD_URL   = 'https://2018285.github.io/rca-bucket-trend-dashboard/dashboard.html'

# Email config — Gmail SMTP with App Password
EMAIL_FROM      = 'selvakumar.s@scootsy.com'
EMAIL_TO        = 'selvakumar.s@scootsy.com'
EMAIL_PASS_FILE = SCRIPT_DIR / 'email_password.txt'

# Source prefix pattern → destination filename (dashboard-expected name)
# The script picks the latest file matching each prefix (sorted by filename desc).
FILE_MAP = {
    'IGCC_IGCC-RCA-Appsheet Summary_Item_level_daily':
        'IGCC-RCA-Appsheet Summary - Item_level_daily.csv',
    'IGCC_IGCC-RCA-Appsheet Summary_Item_level_weekly':
        'IGCC-RCA-Appsheet Summary - Item_level_weekly.csv',
    'IGCC_IGCC-RCA-Appsheet Summary_Spoc_level_':
        'IGCC-RCA-Appsheet Summary - Spoc_level.csv',
    'IGCC_Weekly RCA bucket sumarry_Daily-RCA-Summary':
        'Weekly RCA bucket sumarry - Daily-RCA-Summary.csv',
    'IGCC_Weekly RCA bucket sumarry_WeeklyRCA-Summary':
        'Weekly RCA bucket sumarry - WeeklyRCA-Summary (2).csv',
    'IGCC_Weekly RCA bucket sumarry_City List':
        'Weekly RCA bucket sumarry - City List.csv',
}

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


# ── Email alert ───────────────────────────────────────────────────────────────
def send_alert(subject, failed_files, push_error=None):
    if not EMAIL_PASS_FILE.exists():
        log.warning('email_password.txt not found — skipping email alert.')
        return

    password = EMAIL_PASS_FILE.read_text(encoding='utf-8').strip()
    ts = datetime.now().strftime('%Y-%m-%d %H:%M IST')

    rows = ''.join(
        f'<tr><td style="padding:8px 12px;border-bottom:1px solid #2d3055;"><b>{label}</b></td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #2d3055;color:#f87171;">{reason}</td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #2d3055;color:#8892b0;">{dest}</td></tr>'
        for label, reason, dest in failed_files
    )

    push_section = ''
    if push_error:
        push_section = f'''
        <div style="margin-top:20px;padding:14px 18px;background:#1a1d2e;border-radius:8px;
                    border-left:4px solid #ef4444;">
          <b style="color:#f87171;">&#9888; GitHub Push Failed</b>
          <pre style="margin-top:8px;color:#8892b0;font-size:12px;
                      white-space:pre-wrap;">{push_error}</pre>
        </div>'''

    html = f'''
    <html><body style="background:#0f1117;color:#e2e8f0;
                        font-family:'Segoe UI',system-ui,sans-serif;padding:24px;">
      <div style="max-width:680px;margin:0 auto;">
        <h2 style="color:#f87171;margin-bottom:4px;">
          &#9888; Data Update Failed — {DASHBOARD_NAME}
        </h2>
        <p style="color:#8892b0;margin-top:0;">{ts}</p>
        <p>The scheduled data refresh encountered errors for the following files.
           The dashboard may be showing <b>outdated data</b> until these are resolved.</p>
        <table style="width:100%;border-collapse:collapse;background:#1a1d2e;
                      border-radius:10px;overflow:hidden;margin:16px 0;">
          <thead>
            <tr style="background:#222539;">
              <th style="padding:10px 12px;text-align:left;color:#4f8ef7;">File</th>
              <th style="padding:10px 12px;text-align:left;color:#4f8ef7;">Error</th>
              <th style="padding:10px 12px;text-align:left;color:#4f8ef7;">Destination</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        {push_section}
        <div style="margin-top:24px;padding:14px 18px;background:#1a1d2e;
                    border-radius:8px;border-left:4px solid #4f8ef7;">
          <b style="color:#4f8ef7;">Action Required</b>
          <ol style="margin-top:8px;color:#8892b0;padding-left:18px;line-height:1.8;">
            <li>Place the latest exported CSV files in the
                <code style="background:#222539;padding:2px 6px;border-radius:4px;">RCA CSV Files</code>
                folder next to this script.</li>
            <li>Re-run <code style="background:#222539;padding:2px 6px;border-radius:4px;">
                python update_data.py</code> to retry.</li>
          </ol>
        </div>
        <p style="margin-top:20px;color:#8892b0;font-size:12px;">
          Dashboard: <a href="{DASHBOARD_URL}" style="color:#4f8ef7;">{DASHBOARD_URL}</a><br>
          Log file: <code>update_log.txt</code> in the project folder
        </p>
      </div>
    </body></html>
    '''

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = EMAIL_FROM
    msg['To']      = EMAIL_TO
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_FROM, password)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        log.info('Alert email sent to %s', EMAIL_TO)
    except Exception as exc:
        log.error('Failed to send email: %s', exc)


# ── Copy latest matching file ──────────────────────────────────────────────────
def copy_latest(prefix, dest_path):
    matches = sorted(
        [f for f in CSV_SOURCE_DIR.iterdir()
         if f.name.startswith(prefix) and f.suffix == '.csv'],
        key=lambda f: f.name,
        reverse=True   # latest date suffix sorts last alphabetically → first after reverse
    )
    if not matches:
        raise FileNotFoundError(f'No file found in "{CSV_SOURCE_DIR}" with prefix: {prefix}')
    src = matches[0]
    log.info('  Source: %s', src.name)
    shutil.copy2(src, dest_path)
    if not dest_path.exists() or dest_path.stat().st_size == 0:
        raise RuntimeError('Copied file is empty')
    return src.name


# ── Git push ──────────────────────────────────────────────────────────────────
def git_push(commit_message):
    def run(cmd, check=False):
        r = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
        if r.returncode != 0 and check:
            raise RuntimeError(f"git {' '.join(cmd[1:])} failed:\n{r.stderr.strip()}")
        return r

    run(['git', 'add', '-A'])
    status = run(['git', 'status', '--porcelain'])
    if not status.stdout.strip():
        log.info('No changes to commit — CSV files unchanged.')
        return
    run(['git', 'commit', '-m', commit_message], check=True)
    log.info('Committed.')
    run(['git', 'push', 'origin', 'master'], check=True)
    log.info('Pushed -> %s', DASHBOARD_URL)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info('=' * 60)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    log.info('Data update started  %s IST', ts)

    if not CSV_SOURCE_DIR.exists():
        log.error('Source folder not found: %s', CSV_SOURCE_DIR)
        sys.exit(1)

    updated      = []
    failed_files = []

    for prefix, dest_name in FILE_MAP.items():
        dest = SCRIPT_DIR / dest_name
        log.info('Copying: %s', dest_name)
        try:
            src_name = copy_latest(prefix, dest)
            sz = dest.stat().st_size
            log.info('  OK -> %s  (%s KB)  [from %s]', dest_name, sz // 1024, src_name)
            updated.append(dest_name)
        except Exception as exc:
            reason = str(exc).split('\n')[0][:120]
            log.error('  FAILED %s: %s', dest_name, reason)
            failed_files.append((prefix.split('_')[-1], reason, dest_name))

    log.info('Copied %d/%d files', len(updated), len(FILE_MAP))

    push_error = None
    if updated:
        msg = f'Auto data update {ts} IST ({len(updated)} files refreshed)'
        try:
            git_push(msg)
            log.info('Live dashboard updated successfully.')
        except RuntimeError as exc:
            push_error = str(exc)
            log.error('Git push failed: %s', push_error)
    else:
        log.warning('Nothing copied — skipping git push.')

    if failed_files or push_error:
        subject = f'[{DASHBOARD_NAME}] Data Update Failed — {ts} IST'
        send_alert(subject, failed_files, push_error)

    log.info('=' * 60)


if __name__ == '__main__':
    main()
