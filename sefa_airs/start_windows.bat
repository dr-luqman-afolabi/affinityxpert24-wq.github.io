@echo off
REM SEFA-AIRS one-click start for Windows. Double-click this file.
cd /d "%~dp0"
title SEFA-AIRS
echo Step 1 of 4: looking for Python 3.10 or newer...
set PY=
REM Run each candidate: this skips the Microsoft Store "python" shortcut, which is not a real Python.
py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul && set PY=py -3
if not defined PY python -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul && set PY=python
if not defined PY (
  echo.
  echo PROBLEM: Python 3.10 or newer was not found on this computer.
  echo   1. Install Python from https://www.python.org/downloads/
  echo   2. On the first install screen, tick "Add python.exe to PATH".
  echo   3. Close this window and double-click start_windows.bat again.
  pause
  exit /b 1
)
%PY% --version
if not exist ".venv\Scripts\python.exe" (
  echo Step 2 of 4: creating a private Python environment in .venv ...
  %PY% -m venv .venv || (echo PROBLEM: could not create .venv. Move this folder somewhere simple like C:\SEFA and try again. & pause & exit /b 1)
)
call ".venv\Scripts\activate.bat"
echo Step 3 of 4: installing requirements (needs internet; first run can take a few minutes)...
python -m pip install --disable-pip-version-check -q -r requirements.txt || (echo PROBLEM: package installation failed. Check your internet connection, then send a screenshot of this window. & pause & exit /b 1)
python -c "import sys,app;s=app.SessionLocal();sys.exit(1 if s.query(app.User).count() else 0)"
if not errorlevel 1 (
  echo.
  choice /c DA /m "First run: [D]emo data with made-up students, or [A]dmin account only"
  if errorlevel 2 (python create_admin.py) else (python seed_demo.py)
  if errorlevel 1 (pause & exit /b 1)
)
echo.
echo Step 4 of 4: SEFA-AIRS is starting at http://127.0.0.1:8000  -  keep this window open; close it to stop the app.
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
