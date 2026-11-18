@echo off
rem Runs one scrape locally and pushes the JSON snapshot. Usage: run_local.cmd morning|evening|manual
rem Secrets are read from %USERPROFILE%\.mikser-tracker.env (KEY=VALUE per line), never from the repo.
setlocal
set SLOT=%1
if "%SLOT%"=="" set SLOT=manual
cd /d "%~dp0.."
if not exist logs mkdir logs
if not exist "%USERPROFILE%\.mikser-tracker.env" (
  echo missing %USERPROFILE%\.mikser-tracker.env >> logs\run.log
  exit /b 2
)
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%USERPROFILE%\.mikser-tracker.env") do set "%%a=%%b"
set PYTHONUTF8=1
echo ==== %date% %time% slot=%SLOT% >> logs\run.log
git pull --rebase --autostash -q >> logs\run.log 2>&1
py -3 -m pip install -q -r scraper\requirements.txt >> logs\run.log 2>&1
py -3 -m scraper.pipeline --slot %SLOT% >> logs\run.log 2>&1
git add data/snapshots >> logs\run.log 2>&1
git -c user.name=price-bot -c user.email=price-bot@users.noreply.github.com commit -q -m "snapshot %date% %time%" >> logs\run.log 2>&1
git push -q >> logs\run.log 2>&1
endlocal
