#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse

def ensure_uv():
    """Memastikan uv telah terpasang di virtual environment."""
    try:
        import uv
    except ImportError:
        print("[Info] Memasang uv...")
        subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)

def setup_files():
    """Memastikan requirements.in tersedia sebagai sumber utama."""
    if not os.path.exists("requirements.in"):
        print("[Info] Membuat requirements.in dari requirements.txt...")
        if os.path.exists("requirements.txt"):
            with open("requirements.txt", "r") as f:
                content = f.read()
            with open("requirements.in", "w") as f:
                f.write(content)
        else:
            open("requirements.in", "w").close()

def compile_requirements(upgrade=False):
    """Menghasilkan requirements.txt yang rapi dan terkunci (locked) dari requirements.in."""
    ensure_uv()
    setup_files()

    print("[Info] Meng-compile requirements.txt...")
    cmd = [sys.executable, "-m", "uv", "pip", "compile", "requirements.in", "-o", "requirements.txt"]
    if upgrade:
        cmd.append("--upgrade")

    subprocess.run(cmd, check=True)

    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()

        cleaned = []
        for line in lines:
            if "==" in line and not line.strip().startswith("#"):
                pkg = line.split("==")[0]
                if " #" in line:
                    comment = line[line.index(" #"):]
                    cleaned.append(f"{pkg}{comment}")
                else:
                    cleaned.append(f"{pkg}\n")
            else:
                cleaned.append(line)

        with open("requirements.txt", "w", encoding="utf-8") as f:
            f.writelines(cleaned)
        print("[Info] Berhasil menghapus pin versi dari requirements.txt")
    except Exception as e:
        print(f"[Peringatan] Gagal memodifikasi requirements.txt: {e}")

    print("\n[OK] Berhasil!")

def sync_environment():
    """Menghapus pustaka sampah (orphans) dan menyesuaikan venv dengan requirements.txt."""
    ensure_uv()

    if not os.path.exists("requirements.txt"):
        print("[Error] requirements.txt tidak ditemukan. Jalankan 'python scripts/manage_reqs.py compile' terlebih dahulu.")
        return

    print("[Info] Menyelaraskan environment (.venv) dengan requirements.txt...")
    print("[Info] Paket yang tidak ada di requirements (termasuk sub-dependensi yang usang) akan otomatis dihapus.")

    subprocess.run([sys.executable, "-m", "uv", "pip", "sync", "requirements.txt"], check=True)
    print("\n[OK] Sinkronisasi selesai!")

def add_package(package_name):
    """Menambahkan paket baru ke requirements.in lalu melakukan kompilasi & sinkronisasi."""
    setup_files()

    # Cek apakah paket sudah ada
    with open("requirements.in", "r") as f:
        existing = [line.strip().lower() for line in f.readlines() if line.strip()]

    pkg_clean = package_name.lower().split("=")[0].split(">")[0].split("<")[0].strip()

    if any(pkg_clean in ex for ex in existing):
        print(f"[Info] Paket '{package_name}' tampaknya sudah ada di requirements.in.")
    else:
        with open("requirements.in", "a") as f:
            f.write(f"\n{package_name}\n")
        print(f"[Info] Menambahkan '{package_name}' ke requirements.in...")

    compile_requirements()
    sync_environment()

def main():
    parser = argparse.ArgumentParser(
        description="Script untuk mengelola dependencies Python secara efisien dan bersih menggunakan uv."
    )
    subparsers = parser.add_subparsers(dest="command", help="Daftar perintah")

    # Command: compile
    subparsers.add_parser("compile", help="Generate requirements.txt terkunci dari requirements.in")

    # Command: upgrade
    subparsers.add_parser("upgrade", help="Upgrade semua paket ke versi terbaru yang stabil dan generate ulang requirements.txt")

    # Command: sync
    subparsers.add_parser("sync", help="Install paket dan bersihkan pustaka usang (orphans) dari sistem")

    # Command: add
    parser_add = subparsers.add_parser("add", help="Tambah pustaka baru, compile, lalu sync otomatis")
    parser_add.add_argument("package", help="Nama paket (contoh: requests atau 'requests>=2.25')")

    args = parser.parse_args()

    # Pastikan dijalankan dari root proyek (bisa dicek dari direktori core atau gui)
    if not os.path.exists("core") and not os.path.exists("gui"):
        print("[Peringatan] Harap jalankan script ini dari direktori root")

    if args.command == "compile":
        compile_requirements()
    elif args.command == "upgrade":
        compile_requirements(upgrade=True)
    elif args.command == "sync":
        sync_environment()
    elif args.command == "add":
        add_package(args.package)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
