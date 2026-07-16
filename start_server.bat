@echo off
cd /d "%~dp0"
echo ============================================
echo  RCA Bucket Trend Dashboard
echo ============================================

echo [1/3] Pushing latest changes to GitHub...
<<<<<<< HEAD
git add dashboard.html start_server.bat .gitignore *.csv 2>nul
git add *.csv 2>nul
git diff --cached --quiet
if %errorlevel% neq 0 (
    git commit -m "Update dashboard and data"
    git push origin master
    echo Push complete.
) else (
    echo No changes to push.
=======
python push_github.py
if %errorlevel% neq 0 (
    echo Warning: GitHub push failed, continuing with local server...
>>>>>>> origin/main
)

echo [2/3] Starting local server at http://localhost:8080
echo [3/3] Opening browser...
start "" "http://localhost:8080/dashboard.html"
python -m http.server 8080
if %errorlevel% neq 0 (
<<<<<<< HEAD
    python3 -m http.server 8080
=======
    python -m http.server 8080
>>>>>>> origin/main
)
pause
