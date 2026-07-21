"""Lanzador de escritorio para la distribución Windows de CafBarDLA."""
from threading import Timer
import webbrowser
import os
import sys
from pathlib import Path

base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
os.chdir(base_dir)
import uvicorn
from app.main import app

HOST = "127.0.0.1"
PORT = 8000

if __name__ == "__main__":
    Timer(1.2, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
