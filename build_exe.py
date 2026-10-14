"""Bangun paket .exe portable YDM dengan PyInstaller (Windows).

Hasil: dist\\YDM\\ berisi YDM.exe + YDMNativeHost.exe + extension\\ +
       native_host\\Install-NativeHost-Exe.ps1 + PANDUAN.md (+ tools\\ffmpeg.exe
       bila ditemukan di PC pembangun), lalu YDM-Portable.zip di folder proyek.
Jalankan: python build_exe.py
"""
import os, shutil, struct, subprocess, sys, zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist", "YDM")
WORK = os.path.join(ROOT, "build")

def make_ico():
    # ikon kepala Gundam multi-ukuran yang sudah disiapkan di assets/
    pre = os.path.join(ROOT, "assets", "ydm.ico")
    if os.path.exists(pre):
        return pre
    src = os.path.join(ROOT, "extension", "chromium", "icons", "icon128.png")
    dst = os.path.join(ROOT, "ydm.ico")
    if not os.path.exists(src):
        return None
    png = open(src, "rb").read()
    # ICO dengan gambar PNG tertanam (didukung Windows Vista+)
    ico = struct.pack("<HHH", 0, 1, 1)
    ico += struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 6 + 16)
    open(dst, "wb").write(ico + png)
    return dst

def run(cmd):
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)

def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Memasang PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    ico = make_ico()
    icon_args = ["--icon", ico] if ico else []

    # ---- aplikasi utama (onedir, tanpa jendela konsol) ----
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--onedir", "--windowed", "--name", "YDM",
           "--distpath", os.path.join(ROOT, "dist"),
           "--workpath", WORK,
           "--copy-metadata", "yt-dlp",
           "--collect-submodules", "yt_dlp",
           "--add-data", os.path.join(ROOT, "assets") + os.pathsep + "assets",
           ] + icon_args + ["app.py"]
    try:
        import yt_dlp_ejs  # noqa: F401
        cmd.insert(cmd.index("app.py"), "--collect-submodules")
        cmd.insert(cmd.index("app.py"), "yt_dlp_ejs")
    except Exception:
        pass
    # libtorrent opsional: sertakan penuh bila terpasang di mesin pembangun
    try:
        import libtorrent  # noqa: F401
        cmd.insert(cmd.index("app.py"), "--collect-all")
        cmd.insert(cmd.index("app.py"), "libtorrent")
    except Exception:
        print("libtorrent tidak terpasang: .exe dibangun tanpa torrent bawaan.")
    run(cmd)

    # ---- native host (onefile, konsol/stdio) ----
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
         "--onefile", "--console", "--name", "YDMNativeHost",
         "--distpath", os.path.join(ROOT, "dist"),
         "--workpath", os.path.join(WORK, "host"),
         "native_host_entry.py"])
    shutil.copy2(os.path.join(ROOT, "dist", "YDMNativeHost.exe"),
                 os.path.join(DIST, "YDMNativeHost.exe"))

    # ---- berkas pendamping di samping .exe ----
    shutil.copytree(os.path.join(ROOT, "extension"), os.path.join(DIST, "extension"),
                    dirs_exist_ok=True)
    shutil.copy2(os.path.join(ROOT, "native_host", "Install-NativeHost-Exe.ps1"),
                 os.path.join(DIST, "Install-NativeHost-Exe.ps1"))
    shutil.copy2(os.path.join(ROOT, "PANDUAN.md"), os.path.join(DIST, "PANDUAN.md"))
    with open(os.path.join(DIST, "Install-Ekstensi-Browser-Exe.bat"), "w", encoding="utf-8") as f:
        f.write("@echo off\ncd /d \"%~dp0\"\n"
                "set /p EID=Masukkan ID ekstensi Chromium (dari chrome://extensions):\n"
                "powershell -ExecutionPolicy Bypass -File Install-NativeHost-Exe.ps1 -ExtensionId %EID%\npause\n")

    # ffmpeg untuk PC tujuan yang belum punya: salin dari PATH/FDM mesin pembangun
    from ydm.converter import find_ffmpeg
    ff = find_ffmpeg()
    if ff and os.path.exists(ff):
        os.makedirs(os.path.join(DIST, "tools"), exist_ok=True)
        shutil.copy2(ff, os.path.join(DIST, "tools", "ffmpeg.exe"))
        print(f"ffmpeg disalin dari {ff}")
    else:
        print("ffmpeg tidak ditemukan di mesin pembangun: paket tanpa ffmpeg bawaan.")

    # ---- zip portable ----
    zip_base = os.path.join(ROOT, "YDM-Portable")
    if os.path.exists(zip_base + ".zip"):
        os.remove(zip_base + ".zip")
    shutil.make_archive(zip_base, "zip", os.path.join(ROOT, "dist"), "YDM")
    size_mb = os.path.getsize(zip_base + ".zip") / (1024 * 1024)
    print(f"SELESAI: {DIST}")
    print(f"Portable: {zip_base}.zip ({size_mb:.0f} MB)")

if __name__ == "__main__":
    main()
