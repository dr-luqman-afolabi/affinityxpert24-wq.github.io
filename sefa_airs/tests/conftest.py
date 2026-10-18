"""Run every test against a throwaway SQLite database, never the local sefa.db."""
import os, sys, tempfile
from pathlib import Path

os.environ.setdefault('DATABASE_URL', f"sqlite:///{Path(tempfile.mkdtemp()) / 'test.db'}")
os.environ.setdefault('SESSION_SECRET', 'test-secret')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
