@echo off
REM Rebuilds the NYAYA SETU demo dataset (fresh scenarios S1-S6). Run before each judge demo.
cd /d "%~dp0backend"
if not exist "venv\Scripts\activate.bat" goto :novenv
call "venv\Scripts\activate.bat"
set "DATABASE_URL=sqlite:///./nyaya_setu.db"
python seed.py --reset
if errorlevel 1 goto :fail
echo.
echo Demo data rebuilt. If the API window is open it picks up the new data automatically - just refresh the browser.
pause
exit /b 0
:novenv
echo [X] Run start-local.bat once first.
pause
exit /b 1
:fail
echo [X] Reset failed - scroll up to see the error. Close the API window and try again.
pause
exit /b 1
