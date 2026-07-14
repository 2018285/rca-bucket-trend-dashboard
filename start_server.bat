@echo off
cd /d "%~dp0"
echo ============================================
echo  RCA Bucket Trend Dashboard
echo ============================================
echo Starting local server at http://localhost:8080
echo Opening browser...
start "" "http://localhost:8080/dashboard.html"
python -m http.server 8080
if %errorlevel% neq 0 (
    echo Python not found. Trying python3...
    python3 -m http.server 8080
)
pause
