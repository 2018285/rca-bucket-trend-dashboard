#!/usr/bin/env python3
"""
update_data.py
Downloads the latest CSVs from Google Drive and pushes to GitHub.
Scheduled to run at 10:30 AM and 3:00 PM IST via Windows Task Scheduler.
"""

import io
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── Config ────────────────────────────────────────────────────────────────────
SCOPES          = ['https://www.googleapis.com/auth/drive.readonly']
DRIVE_FOLDER_ID = '1dWSFOJK_hAMDlIcxGHH8RPihTqhd7OIf'
SCRIPT_DIR      = Path(__file__).parent
TOKEN_PATH      = SCRIPT_DIR / 'token.json'
CREDS_PATH      = SCRIPT_DIR / 'credentials.json'
LOG_PATH        = SCRIPT_DIR / 'update_log.txt'

# (drive_name_contains, drive_name_must_NOT_contain) → local filename
FILE_MAP = [
    (('Item_level_daily',    None),   'IGCC-RCA-Appsheet Summary - Item_level_daily.csv'),
    (('Item_level_weekly',   None),   'IGCC-RCA-Appsheet Summary - Item_level_weekly.csv'),
    (('Spoc_level (D-2)',    None),   'IGCC-RCA-Appsheet Summary - Spoc_level (D-2).csv'),
    (('Spoc_level',          'D-2'),  'IGCC-RCA-Appsheet Summary - Spoc_level.csv'),
    (('Daily-RCA-Summary',   None),   'Weekly RCA bucket sumarry - Daily-RCA-Summary.csv'),
    (('WeeklyRCA-Summary',   None),   'Weekly RCA bucket sumarry - WeeklyRCA-Summary (2).csv'),
    (('City List',           None),   'Weekly RCA bucket sumarry - City List.csv'),
]

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


# ── Google Drive Auth ─────────────────────────────────────────────────────────
def get_credentials():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                log.error('credentials.json not found at %s', CREDS_PATH)
                log.error('See SETUP.md for instructions to create it.')
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding='utf-8')
    return creds


# ── Drive helpers ─────────────────────────────────────────────────────────────
def find_latest_file(service, must_contain, must_not_contain):
    """Return (file_id, file_name) of the newest matching file in the Drive folder."""
    # Escape single quotes in the search term
    escaped = must_contain.replace("'", "\\'")
    q = (
        f"'{DRIVE_FOLDER_ID}' in parents"
        f" and name contains '{escaped}'"
        f" and mimeType != 'application/vnd.google-apps.folder'"
        f" and trashed = false"
    )
    result = service.files().list(
        q=q,
        orderBy='modifiedTime desc',
        pageSize=10,
        fields='files(id,name,modifiedTime)'
    ).execute()
    items = result.get('files', [])
    if must_not_contain:
        items = [f for f in items if must_not_contain not in f['name']]
    if not items:
        return None, None
    return items[0]['id'], items[0]['name']


def download_file(service, file_id, dest_path):
    """Download a Drive file by ID to dest_path."""
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request, chunksize=10 * 1024 * 1024)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    dest_path.write_bytes(buf.getvalue())


# ── Git push ──────────────────────────────────────────────────────────────────
def git_push(commit_message):
    def run(cmd, check=False):
        r = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
        if r.returncode != 0 and check:
            log.error('Command failed: %s\n%s', ' '.join(cmd), r.stderr.strip())
            sys.exit(1)
        return r

    run(['git', 'add', '-A'])

    status = run(['git', 'status', '--porcelain'])
    if not status.stdout.strip():
        log.info('No changes to commit — CSV files unchanged.')
        return False

    r = run(['git', 'commit', '-m', commit_message], check=True)
    log.info('Committed: %s', r.stdout.strip())

    r = run(['git', 'push', 'origin', 'master'], check=True)
    log.info('Pushed to GitHub → https://2018285.github.io/rca-bucket-trend-dashboard/dashboard.html')
    return True


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info('=' * 60)
    log.info('Data update started at %s IST', datetime.now().strftime('%Y-%m-%d %H:%M'))

    creds   = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    updated = []
    errors  = []

    for (must_contain, must_not), local_name in FILE_MAP:
        log.info('Looking for: %s', must_contain)
        try:
            fid, drive_name = find_latest_file(service, must_contain, must_not)
            if not fid:
                log.warning('  Not found in Drive, skipping: %s', local_name)
                errors.append(local_name)
                continue
            log.info('  Matched: %s', drive_name)
            dest = SCRIPT_DIR / local_name
            download_file(service, fid, dest)
            sz = dest.stat().st_size
            log.info('  Saved → %s  (%s KB)', dest.name, sz // 1024)
            updated.append(local_name)
        except Exception as exc:
            log.error('  Error downloading %s: %s', local_name, exc)
            errors.append(local_name)

    log.info('Downloaded %d/%d files', len(updated), len(FILE_MAP))

    if errors:
        log.warning('Skipped: %s', ', '.join(errors))

    if not updated:
        log.warning('Nothing downloaded — skipping git push.')
        return

    ts  = datetime.now().strftime('%Y-%m-%d %H:%M')
    msg = f'Auto data update: {ts} IST ({len(updated)} files refreshed)'
    pushed = git_push(msg)
    if pushed:
        log.info('Live dashboard updated successfully.')
    log.info('=' * 60)


if __name__ == '__main__':
    main()
