# install_requirements.py
import subprocess
import sys
import time
from pathlib import Path

REQ_FILE = Path("requirements.txt")

def run(cmd, check=True):
    print(f"\n> {' '.join(cmd)}")
    proc = subprocess.run(cmd)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc.returncode

def main():
    if not REQ_FILE.exists():
        print(f"requirements.txt not found at {REQ_FILE.resolve()}")
        raise SystemExit(1)

    # Upgrade pip for smoother installs
    try:
        run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=False)
    except Exception:
        pass

    retries = 3
    for attempt in range(1, retries + 1):
        print(f"\nInstalling from {REQ_FILE} (attempt {attempt}/{retries}) ...")
        code = run([sys.executable, "-m", "pip", "install", "-r", str(REQ_FILE)], check=False)
        if code == 0:
            print("\nAll requirements installed successfully.")
            return
        if attempt < retries:
            wait = 3 * attempt
            print(f"Install failed (code {code}). Retrying in {wait}s ...")
            time.sleep(wait)

    print("\nInstallation failed after retries. Check your internet connection or proxy and try again.")
    raise SystemExit(code)

if __name__ == "__main__":
    main()
