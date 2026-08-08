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

    from core.security import obfuscate

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY", "")

    obfuscated_url = obfuscate(supabase_url)
    obfuscated_key = obfuscate(supabase_key)

    with open(os.path.join("core", "_build_env.py"), "w", encoding="utf-8") as f:
        f.write("# Auto-generated during build\n")
        f.write(f'SUPABASE_URL_OBFUSCATED = "{obfuscated_url}"\n')
        f.write(f'SUPABASE_SECRET_KEY_OBFUSCATED = "{obfuscated_key}"\n')


def install_build_dependencies(target_platform):
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print("[INFO] Running in GitHub Actions. Skipping dependency installation as runners have pre-installed tools.")
        return

    print(f"[INFO] Checking and installing build dependencies for platform: {target_platform}...")
    if target_platform == "linux":
        if shutil.which("apt-get"):
            print("[INFO] Debian/Ubuntu system detected. Installing dependencies via apt...")
            try:
                cmd = ["sudo", "apt-get", "update"]
                print(f"[RUN] {' '.join(cmd)}")
                subprocess.run(cmd, check=True)

                cmd = ["sudo", "apt-get", "install", "-y", "clang", "cmake", "ninja-build", "pkg-config", "libgtk-3-dev", "liblzma-dev", "libmpv-dev"]
                print(f"[RUN] {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
                print("[OK] Dependencies installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"[WARNING] Failed to automatically install dependencies: {e}")
                print("[WARNING] Please run the following command manually to install dependencies:")
                print("    sudo apt-get update && sudo apt-get install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev")
        else:
            print("[WARNING] Package manager 'apt-get' not found. Please install building tools (clang, cmake, ninja-build, pkg-config, gtk3-dev, lzma-dev) manually.")

    elif target_platform == "macos":
        if shutil.which("brew"):
            print("[INFO] macOS system detected. Installing dependencies via Homebrew...")
            try:
                cmd = ["brew", "install", "cmake", "ninja"]
                print(f"[RUN] {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
                print("[OK] Dependencies installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"[WARNING] Failed to automatically install dependencies: {e}")
                print("[WARNING] Please run: brew install cmake ninja")
        else:
            print("[WARNING] Homebrew ('brew') not found. Please install 'cmake' and 'ninja' manually.")

    elif target_platform == "windows":
        print("[INFO] Windows system detected.")
        print("[INFO] Visual Studio 2022 Build Tools (with C++ Desktop workload) is required.")
        print("[INFO] Attempting to install via winget...")
        if shutil.which("winget"):
            try:
                cmd = ["winget", "install", "--id", "Microsoft.VisualStudio.2022.BuildTools", "--exact", "--silent", "--override", "--add Microsoft.VisualStudio.Workload.VCTools;includeRecommended"]
                print(f"[RUN] {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
                print("[OK] VS Build Tools installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"[WARNING] Failed to automatically install Visual Studio Build Tools: {e}")
                print("[WARNING] Please install 'Desktop development with C++' workload using Visual Studio Installer manually.")
        else:
            print("[WARNING] 'winget' not found. Please download and install Visual Studio with C++ desktop workload manually.")


def main():
    print("=== Cliptzy Standalone Build System (Flet) ===")

    import argparse
    parser = argparse.ArgumentParser(description="Cliptzy Standalone Build System")
    args = parser.parse_args()

    generate_build_env()

    # 1. Determine target platform
    target_platform = "linux"
    if sys.platform == "win32":
        target_platform = "windows"
    elif sys.platform == "darwin":
        target_platform = "macos"

    print(f"[INFO] Target platform identified: {target_platform}")

    # 2. Locate flet executable
    flet_bin_name = "flet.exe" if sys.platform == "win32" else "flet"
    flet_bin = os.path.join(os.path.dirname(sys.executable), flet_bin_name)

    if not os.path.exists(flet_bin):
        # Fallback to system PATH
        flet_bin = shutil.which(flet_bin_name)

    if not flet_bin:
        print("[ERROR] Flet executable not found! Make sure 'flet' is installed in the active environment.")
        sys.exit(1)

    print(f"[OK] Flet executable located: {flet_bin}")

    # Install platform build dependencies
    install_build_dependencies(target_platform)

    # 3. Execute flet build
    dist_dir = os.path.join("dist", "cliptzy")
    print(f"[BUILD] Building Flet app for {target_platform}...")

    cmd = [flet_bin, "build", target_platform, "--python-version", "3.13", "-o", dist_dir, "-v"]

    # Explicitly exclude heavy/unneeded directories to prevent tmpfs disk quota issues
    exclude_list = [
        ".git", ".github", ".venv", "venv", "clips", "logs", "build", "dist", "__pycache__",
        "*.log", ".env", "*.md", "cred", "*.json",
        "tests", "*.sql", ".gitignore", "requirements.in"
    ]
    cmd.append("--exclude")
    cmd.extend(exclude_list)
    cmd.append("--no-compile-packages")

    print(f"[RUN] {' '.join(cmd)}")

    print("[BUILD] Generating requirements.txt via uv export...")
    try:
        subprocess.run(["uv", "export", "--no-hashes", "--no-emit-project", "-o", "requirements.txt"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to generate requirements.txt: {e}")
        sys.exit(1)
    res = subprocess.run(cmd)

    if res.returncode != 0:
        print("[ERROR] Flet build failed!")
        sys.exit(res.returncode)

    print(f"[SUCCESS] Standalone build completed successfully!")
    print(f"[OUTPUT] Executable folder located at: {os.path.abspath(dist_dir)}")

if __name__ == "__main__":
    main()
