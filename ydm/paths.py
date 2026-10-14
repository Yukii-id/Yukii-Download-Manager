import os, sys

def is_frozen():
    return bool(getattr(sys, "frozen", False))

def app_root():
    """Folder aplikasi: folder .exe bila frozen (PyInstaller), else folder proyek."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    # berkas ini di <root>/ydm/paths.py -> root proyek dua tingkat ke atas
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def data_dir():
    return os.path.join(app_root(), "data")

def standalone_ytdlp_path(data=None):
    d = os.path.join(data or data_dir(), "bin")
    return os.path.join(d, "yt-dlp.exe" if sys.platform.startswith("win") else "yt-dlp")
