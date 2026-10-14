"""Peluncur YDM: pastikan dependensi ada (unduh sekali, butuh internet),
lalu jalankan aplikasi utama."""
import subprocess, sys

def ensure():
    try:
        import PySide6  # noqa: F401
        import yt_dlp  # noqa: F401
        return
    except ImportError:
        pass
    print("Memasang dependensi (PySide6 + yt-dlp, sekali saja, butuh internet)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

if __name__ == "__main__":
    ensure()
    import app
    app.main()
