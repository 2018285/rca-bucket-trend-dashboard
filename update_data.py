#!/usr/bin/env python3
"""
update_data.py
Downloads the latest CSVs from Google Drive and pushes to GitHub.
On any failure, sends an alert email via Gmail to selvakumar.s@scootsy.com.
Scheduled via Windows Task Scheduler at 10:30 AM and 3:00 PM IST daily.
"""

import sys
import smtplib
import logging
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

import gdown

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR      = Path(__file__).parent
LOG_PATH        = SCRIPT_DIR / 'update_log.txt'
DASHBOARD_NAME  = 'RCA Bucket Trend Dashboard'
DASHBOARD_URL   = 'https://2018285.github.io/rca-bucket-trend-dashboard/dashboard.html'
DRIVE_FOLDER_ID = '1dWSFOJK_hAMDlIcxGHH8RPihTqhd7OIf'
DRIVE_FOLDER_URL = f'https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}'

# Email config — Gmail SMTP with App Password
EMAIL_FROM    = 'selvakumar.s@scootsy.com'
EMAIL_TO      = 'selvakumar.s@scootsy.com'
# Store your Gmail App Password in a file called email_password.txt next to this script.
# (Google Account → Security → 2-Step Verification → App passwords → generate one)
EMAIL_PASS_FILE = SCRIPT_DIR / 'email_password.txt'

# Drive file ID → local filename
STATIC_FILE_MAP = {
    'Item_level_daily':  ('1KJZ4_02wva77DJobW3k7wELS3Dh7slml',
                          'IGCC-RCA-Appsheet Summary - Item_level_daily.csv'),
    'Item_level_weekly': ('10xjAlXibnSJA8eg2rQPAzjOu9I6HhurZ',
                          'IGCC-RCA-Appsheet Summary - Item_level_weekly.csv'),
    'Spoc_level':        ('1B2eOucZ-kDSRyHPQpmOhFWWogAU1EPzJ',
                          'IGCC-RCA-Appsheet Summary - Spoc_level.csv'),
    'Spoc_level (D-2)':  ('16xGp3qRX1J1Ach6sepB9m7tCU3YFugKr',
                          'IGCC-RCA-Appsheet Summary - Spoc_level (D-2).csv'),
    'Daily-RCA-Summary': ('1vtjpTn5FO8iCiLc-4sjLnMIaMj2KjlFh',
                          'Weekly RCA bucket sumarry - Daily-RCA-Summary.csv'),
    'WeeklyRCA-Summary': ('1HIX010n_XTAoWzhSmGguCwhUYmdSKbk-',
                          'Weekly RCA bucket sumarry - WeeklyRCA-Summary (2).csv'),
    'City List':         ('1BQqg3EupdThqmFw6x8NS3pgGPinMdNy6',
                          'Weekly RCA bucket sumarry - City List.csv'),
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
    """Send failure alert email. Skips silently if no password file."""
    if not EMAIL_PASS_FILE.exists():
        log.warning('email_password.txt not found — skipping email alert.')
        return

    password = EMAIL_PASS_FILE.read_text(encoding='utf-8').strip()
    ts = datetime.now().strftime('%Y-%m-%d %H:%M IST')

    # Build HTML body
    rows = ''.join(
        f'<tr><td style="padding:8px 12px;border-bottom:1px solid #2d3055;">'
        f'<b>{label}</b></td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #2d3055;color:#f87171;">{reason}</td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #2d3055;color:#8892b0;">{local}</td></tr>'
        for label, reason, local in failed_files
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
              <th style="padding:10px 12px;text-align:left;color:#4f8ef7;">Local Name</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>

        {push_section}

        <div style="margin-top:24px;padding:14px 18px;background:#1a1d2e;
                    border-radius:8px;border-left:4px solid #4f8ef7;">
          <b style="color:#4f8ef7;">Action Required</b>
          <ol style="margin-top:8px;color:#8892b0;padding-left:18px;line-height:1.8;">
            <li>Open the <a href="{DRIVE_FOLDER_URL}" style="color:#4f8ef7;">
                Google Drive folder</a> and verify the files are present and up to date.</li>
            <li>If files are missing, upload the latest exports to the Drive folder.</li>
            <li>Re-run <code style="background:#222539;padding:2px 6px;border-radius:4px;">
                python update_data.py</code> manually to retry.</li>
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


# ── Download ──────────────────────────────────────────────────────────────────
def download(file_id, dest_path):
    url = f'https://drive.google.com/uc?id={file_id}'
    gdown.download(url, str(dest_path), quiet=False)
    if not dest_path.exists() or dest_path.stat().st_size == 0:
        raise RuntimeError('Download produced empty file — file may not be publicly shared')


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
        return True, None

    run(['git', 'commit', '-m', commit_message], check=True)
    log.info('Committed.')
    run(['git', 'push', 'origin', 'master'], check=True)
    log.info('Pushed → %s', DASHBOARD_URL)
    return True, None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info('=' * 60)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    log.info('Data update started  %s IST', ts)

    updated      = []
    failed_files = []   # (label, error_reason, local_name)

    for label, (file_id, local_name) in STATIC_FILE_MAP.items():
        dest = SCRIPT_DIR / local_name
        log.info('Downloading: %s', label)
        try:
            download(file_id, dest)
            sz = dest.stat().st_size
            log.info('  OK → %s  (%s KB)', local_name, sz // 1024)
            updated.append(local_name)
        except Exception as exc:
            reason = str(exc).split('\n')[0][:120]
            log.error('  FAILED %s: %s', local_name, reason)
            failed_files.append((label, reason, local_name))

    log.info('Downloaded %d/%d files', len(updated), len(STATIC_FILE_MAP))

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
        log.warning('Nothing downloaded — skipping git push.')

    # Send alert if anything failed
    if failed_files or push_error:
        subject = f'[{DASHBOARD_NAME}] Data Update Failed — {ts} IST'
        send_alert(subject, failed_files, push_error)

    log.info('=' * 60)


if __name__ == '__main__':
    main()
