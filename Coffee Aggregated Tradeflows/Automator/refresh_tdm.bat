@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  TDM coffee exports refresh (all origins)
echo ============================================
echo.

python tdm_exports_ingest.py %*
if errorlevel 1 (
    echo.
    echo  REFRESH FAILED - see error above.
    echo  The existing parquet was left untouched.
    pause
    exit /b 1
)

echo.
echo  Done. Run refresh_and_publish.bat (one level up) to validate and push.
pause
