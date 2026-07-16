import base64
import json
import ssl
import urllib.request
import urllib.error
import os
import sys

# Token is read from a local config file (not committed to git)
# File: .github_token (one line: your GitHub Personal Access Token)
def load_token():
    token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github_token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            return f.read().strip()
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token
    print("ERROR: No token found. Create .github_token file with your PAT.")
    sys.exit(1)

TOKEN = load_token()
REPO = "2018285/rca-bucket-trend-dashboard"
BRANCH = "main"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API = "https://api.github.com"

FILES = [
    "dashboard.html",
    ".gitignore",
    "start_server.bat",
    "push_github.py",
    "IGCC-RCA-Appsheet Summary - Item_level_daily.csv",
    "IGCC-RCA-Appsheet Summary - Item_level_weekly.csv",
    "IGCC-RCA-Appsheet Summary - Spoc_level.csv",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api_call(method, path, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "RCA-Dashboard-Uploader")
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"HTTP {e.code}: {body_text}", file=sys.stderr)
        raise

print("Pushing to GitHub...")

ref = api_call("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH}")
base_commit_sha = ref["object"]["sha"]

commit_obj = api_call("GET", f"/repos/{REPO}/git/commits/{base_commit_sha}")
base_tree_sha = commit_obj["tree"]["sha"]

tree_items = []
for fname in FILES:
    filepath = os.path.join(BASE_DIR, fname)
    if not os.path.exists(filepath):
        print(f"  Skipping (not found): {fname}")
        continue
    print(f"  Uploading: {fname} ({os.path.getsize(filepath):,} bytes)")
    with open(filepath, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("ascii")
    blob = api_call("POST", f"/repos/{REPO}/git/blobs", {
        "content": content_b64,
        "encoding": "base64"
    })
    tree_items.append({"path": fname, "mode": "100644", "type": "blob", "sha": blob["sha"]})

tree = api_call("POST", f"/repos/{REPO}/git/trees", {
    "base_tree": base_tree_sha,
    "tree": tree_items
})

commit = api_call("POST", f"/repos/{REPO}/git/commits", {
    "message": "Auto-update dashboard and data",
    "tree": tree["sha"],
    "parents": [base_commit_sha]
})

api_call("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {
    "sha": commit["sha"],
    "force": False
})

print(f"Done! Live at: https://2018285.github.io/rca-bucket-trend-dashboard/dashboard.html")
