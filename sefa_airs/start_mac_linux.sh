#!/bin/sh
# SEFA-AIRS start for macOS/Linux. Usage: sh start_mac_linux.sh        (this computer only)
#                                         sh start_mac_linux.sh network (other computers on the network too)
cd "$(dirname "$0")" || exit 1
HOST=127.0.0.1; [ "$1" = "network" ] && HOST=0.0.0.0
PY=$(command -v python3 || command -v python) || { echo "Install Python 3.10+ from https://www.python.org/downloads/"; exit 1; }
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "Python 3.10 or newer is required"; exit 1; }
[ -x .venv/bin/python ] || "$PY" -m venv .venv || exit 1
. .venv/bin/activate
python -m pip install --disable-pip-version-check -q -r requirements.txt || exit 1
if python -c "import sys,app;s=app.SessionLocal();sys.exit(1 if s.query(app.User).count() else 0)"; then
  printf "First run: [D]emo data with made-up students, or [A]dmin account only? "; read -r ans
  case "$ans" in [Aa]*) python create_admin.py ;; *) python seed_demo.py ;; esac || exit 1
fi
echo "SEFA-AIRS: open http://127.0.0.1:8000 on this computer"
[ "$HOST" = 0.0.0.0 ] && echo "Other computers: http://$(python -c "import socket;s=socket.socket(2,2);s.connect(('10.255.255.255',1));print(s.getsockname()[0])"):8000"
exec python -m uvicorn app:app --host "$HOST" --port 8000
