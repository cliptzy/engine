"""
Automated Build Script for Cliptzy Standalone Executable (PyInstaller)
"""

import os
import sys
import subprocess
import shutil

def generate_build_env():
    print("[INFO] Generating core/_build_env.py...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY", "")
    
    with open(os.path.join("core", "_build_env.py"), "w", encoding="utf-8") as f:
        f.write("# Auto-generated during build\n")
        f.write(f'SUPABASE_URL = "{supabase_url}"\n')
        f.write(f'SUPABASE_SECRET_KEY = "{supabase_key}"\n')

def main():
    print("=== Cliptzy Standalone Build System ===")
    
    generate_build_env()
    
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
