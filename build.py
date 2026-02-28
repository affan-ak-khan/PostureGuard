"""
build.py — Build PostureGuard into a standalone .exe
Usage:  python build.py

Steps performed:
  1. Generate .ico from app_icon.png (if missing)
  2. Run PyInstaller with PostureGuard.spec
  3. Copy runtime-writable folders (data/, logs/) into output
  4. Print summary
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "PostureGuard"


def generate_ico():
    """Convert assets/icons/app_icon.png → .ico using Pillow."""
    png = ROOT / "assets" / "icons" / "app_icon.png"
    ico = ROOT / "assets" / "icons" / "app_icon.ico"
    if ico.exists():
        print(f"[✓] Icon already exists: {ico.relative_to(ROOT)}")
        return
    if not png.exists():
        print("[!] No app_icon.png found — skipping icon generation")
        return
    try:
        from PIL import Image
        img = Image.open(png)
        # Multi-size .ico for crisp rendering at different DPIs
        img.save(str(ico), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(f"[✓] Generated {ico.relative_to(ROOT)}")
    except ImportError:
        print("[!] Pillow not found — icon will not be embedded. Install with: pip install Pillow")


def run_pyinstaller():
    """Run PyInstaller with the spec file."""
    spec = ROOT / "PostureGuard.spec"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec),
    ]
    print(f"\n[*] Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("\n[✗] PyInstaller failed!")
        sys.exit(1)
    print("\n[✓] PyInstaller completed successfully")


def copy_runtime_dirs():
    """Create empty data/ and logs/ folders in the distribution."""
    for folder in ("data", "logs"):
        target = DIST / folder
        target.mkdir(parents=True, exist_ok=True)
        print(f"[✓] Created {target.relative_to(ROOT)}")


def create_shortcut_info():
    """Print instructions for creating a desktop shortcut."""
    exe_path = DIST / "PostureGuard.exe"
    print(f"""
{'='*60}
  BUILD COMPLETE!
{'='*60}

  Output folder : {DIST}
  Executable    : {exe_path}

  TO SHARE WITH A FRIEND:
  1. Zip the entire folder:
     dist/PostureGuard/

  2. Send the .zip to your friend

  3. They extract it and double-click:
     PostureGuard.exe

  TO CREATE A DESKTOP SHORTCUT:
  - Right-click PostureGuard.exe → Send to → Desktop (create shortcut)
  - Or drag PostureGuard.exe to the Desktop while holding Alt

{'='*60}
""")


if __name__ == "__main__":
    print(f"Building PostureGuard from: {ROOT}\n")
    generate_ico()
    run_pyinstaller()
    copy_runtime_dirs()
    create_shortcut_info()
