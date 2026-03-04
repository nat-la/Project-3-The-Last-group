import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

BACKEND_URL = "http://127.0.0.1:8000/docs"
FRONTEND_URL = "http://localhost:5173"

def run(cmd, cwd):
    return subprocess.Popen(cmd, cwd=str(cwd), shell=False)

def main():
    # --- Start backend ---
    # assumes you already created/activated venv at least once.
    # If you want, you can add auto-venv creation too.
    python = BACKEND / "venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    if not python.exists():
        print("Backend venv not found. Create it first:")
        print("  cd backend")
        print("  python -m venv venv")
        print("  venv\\Scripts\\python -m pip install -r requirements.txt   (Windows)")
        print("  venv/bin/python -m pip install -r requirements.txt        (Linux/Mac)")
        sys.exit(1)

    backend_proc = run([str(python), "-m", "uvicorn", "app.api:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], BACKEND)
    print("Backend started.")

    # --- Start frontend ---
    # Ensure deps are installed
    npm = "npm.cmd" if os.name == "nt" else "npm"
    # run npm install only if node_modules missing
    if not (FRONTEND / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.check_call([npm, "install"], cwd=str(FRONTEND))

    frontend_proc = run([npm, "run", "dev"], FRONTEND)
    print("Frontend started.")

    # --- Open browser ---
    time.sleep(2)
    webbrowser.open(FRONTEND_URL)

    # Keep running until user stops
    print("\nRunning. Press Ctrl+C to stop.")
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()