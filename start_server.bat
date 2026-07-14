@echo off
cd /d "%~dp0"
echo ============================================
echo  RCA Bucket Trend Dashboard
echo ============================================

echo [1/3] Pushing latest changes to GitHub...
python push_github.py
if %errorlevel% neq 0 (
    echo Warning: GitHub push failed, continuing with local server...
)

echo [2/3] Starting local server at http://localhost:8080
echo [3/3] Opening browser...
start "" "http://localhost:8080/dashboard.html"
python -m http.server 8080
if %errorlevel% neq 0 (
    python -m http.server 8080
)
pause
