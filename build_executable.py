"""
Automated Build Script for Cliptzy Standalone Executable (PyInstaller)
"""

import os
import sys
import subprocess
import shutil

def main():
    print("=== Cliptzy Standalone Build System ===")
    
    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller is available (version {PyInstaller.__version__})")
    except ImportError:
        print("[INFO] Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("[OK] PyInstaller installed successfully.")

    # 2. Run PyInstaller build with cliptzy.spec
    spec_path = "cliptzy.spec"
    if not os.path.exists(spec_path):
        print(f"[ERROR] Spec file '{spec_path}' not found!")
        sys.exit(1)

    print(f"[BUILD] Building standalone executable using {spec_path}...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_path]
    res = subprocess.run(cmd)

    if res.returncode != 0:
        print("[ERROR] PyInstaller build failed!")
        sys.exit(res.returncode)

    dist_dir = os.path.join("dist", "cliptzy")
    print(f"[SUCCESS] Standalone build completed successfully!")
    print(f"[OUTPUT] Executable folder located at: {os.path.abspath(dist_dir)}")

if __name__ == "__main__":
    main()
