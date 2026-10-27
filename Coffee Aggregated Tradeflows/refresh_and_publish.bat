@echo off
setlocal
cd /d "%~dp0"

rem Dashboard Entry saves commit straight to GitHub - take them first.
git pull --rebase --autostash -q

echo ============================================
echo  Step 1/4: TDM coffee exports refresh
echo ============================================
echo.

python "Automator\tdm_exports_ingest.py" %*
if errorlevel 1 (
    echo.
    echo  REFRESH FAILED - see error above.
    echo  The existing parquet was left untouched. Nothing was pushed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Step 2/4: Validating the Database files
echo ============================================
echo.

python "Automator\validate_data.py"
if errorlevel 1 (
    echo.
    echo ============================================
    echo  VALIDATION FAILED - nothing was pushed.
    echo  Fix the issues above in the Database\ files, then run this again.
    echo ============================================
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Step 3/4: Checking for changes
echo ============================================
echo.

git diff --quiet -- "Database\tdm_exports.parquet" "Database\manual_exports.csv" "Database\settings.json" "Database\history_exports.csv"
if not errorlevel 1 (
    echo No changes detected - nothing to push.
    pause
    exit /b 0
)

echo.
echo ============================================
echo  Step 4/4: Committing and pushing to GitHub
echo ============================================
echo.

git add "Database\tdm_exports.parquet" "Database\manual_exports.csv" "Database\settings.json" "Database\history_exports.csv"
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm\""') do set STAMP=%%i
git commit -m "Data update %STAMP%"
if errorlevel 1 (
    echo.
    echo Commit failed - see error above.
    pause
    exit /b 1
)

git push
if errorlevel 1 (
    echo.
    echo Push failed - see error above. Your commit is still saved locally;
    echo ask for help before trying again.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Done. Streamlit Cloud will redeploy within
echo  about a minute.
echo ============================================
pause
