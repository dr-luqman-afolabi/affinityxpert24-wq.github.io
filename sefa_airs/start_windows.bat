@echo off
REM SEFA-AIRS one-click start for Windows. Double-click this file.
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set PY=py
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo Python 3.11 or newer is required. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during installation, then run this file again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY% -m venv .venv || (pause & exit /b 1)
)
call ".venv\Scripts\activate.bat"
echo Installing requirements (first run can take a few minutes)...
python -m pip install --disable-pip-version-check -q -r requirements.txt || (echo Package installation failed. & pause & exit /b 1)
python -c "import sys,app;s=app.SessionLocal();sys.exit(1 if s.query(app.User).count() else 0)"
if not errorlevel 1 (
  echo.
  choice /c DA /m "First run: [D]emo data with made-up students, or [A]dmin account only"
  if errorlevel 2 (python create_admin.py) else (python seed_demo.py)
  if errorlevel 1 (pause & exit /b 1)
)
echo.
echo SEFA-AIRS is starting at http://127.0.0.1:8000  -  keep this window open; close it to stop the app.
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
