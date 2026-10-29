@echo off
REM ===================================================================
REM  NYAYA SETU - one-click local start (no Docker, no PostgreSQL)
REM  Uses a local SQLite database file: backend\nyaya_setu.db
REM ===================================================================
setlocal
cd /d "%~dp0"
set "ROOT=%~dp0"

if exist "%ROOT%tools\node\node.exe" set "PATH=%ROOT%tools\node;%PATH%"

where python >nul 2>nul
if errorlevel 1 goto :nopython
where npm >nul 2>nul
if errorlevel 1 goto :nonode

set "DATABASE_URL=sqlite:///./nyaya_setu.db"

echo.
echo [1/4] Preparing Python environment - first run takes a few minutes...
cd /d "%ROOT%backend"
if not exist "venv\Scripts\activate.bat" python -m venv venv
if not exist "venv\Scripts\activate.bat" goto :venvfail
call "venv\Scripts\activate.bat"
REM Install packages only once, so the app also starts without internet (e.g. at the venue).
if exist "venv\.nyaya_deps_ok" goto :depsok
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :pipfail
echo ok> "venv\.nyaya_deps_ok"
goto :afterdeps
:depsok
echo     Python packages already installed - skipping. Delete backend\venv\.nyaya_deps_ok to reinstall.
:afterdeps

echo.
echo [2/4] Creating demo database...
if exist "nyaya_setu.db" goto :dbexists
python seed.py --reset
if errorlevel 1 goto :seedfail
goto :startapi
:dbexists
echo     Database already exists. Delete backend\nyaya_setu.db to rebuild the demo data.

:startapi
echo.
echo [3/4] Starting API on http://localhost:8000 ...
start "NYAYA SETU - API" /D "%ROOT%backend" cmd /k "set DATABASE_URL=sqlite:///./nyaya_setu.db&& call venv\Scripts\activate.bat&& uvicorn app.main:app --reload --port 8000"

echo.
echo [4/4] Starting web app on http://localhost:5173 ...
cd /d "%ROOT%frontend"
if exist "node_modules\.bin\vite.cmd" goto :fonts
call npm install
if errorlevel 1 goto :npmfail
:fonts
REM Self-hosted fonts so the UI looks identical offline. Best effort: skipped if no internet.
if exist "node_modules\@fontsource\cinzel" goto :startweb
call npm install --no-audit --no-fund
if errorlevel 1 echo     [!] Could not download offline fonts - the app still works; fonts load online.

:startweb
start "NYAYA SETU - Web" /D "%ROOT%frontend" cmd /k "npm run dev"
timeout /t 8 >nul
start "" http://localhost:5173
echo.
echo Done. Two windows are running: API and Web. Close them to stop.
echo Login: management@aicte.demo / Demo@123456  - or use the one-click demo buttons.
pause
exit /b 0

:nopython
echo [X] Python not found. Install Python 3.12 from python.org and tick "Add python.exe to PATH".
pause
exit /b 1
:nonode
echo [X] Node.js not found. Put portable Node in tools\node - see chat instructions.
pause
exit /b 1
:venvfail
echo [X] Could not create the Python virtual environment.
pause
exit /b 1
:pipfail
echo [X] pip install failed - scroll up to see the error.
pause
exit /b 1
:seedfail
echo [X] Seeding the demo database failed - scroll up to see the error.
pause
exit /b 1
:npmfail
echo [X] npm install failed - scroll up to see the error.
pause
exit /b 1
