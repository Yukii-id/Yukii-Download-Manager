import os

CATEGORIES = {
    "Program": {".exe", ".msi", ".dmg", ".apk", ".deb", ".rpm", ".iso", ".img"},
    "Arsip": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"},
    "Musik": {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"},
    "Dokumen": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".epub"},
    "Gambar": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"},
    "Torrent": {".torrent"},
}

def category_for(filename):
    ext = os.path.splitext(filename or "")[1].lower()
    for name, exts in CATEGORIES.items():
        if ext in exts:
            return name
    return "Lainnya"

def target_dir(base_dir, filename, smart_sort=True):
    if not smart_sort:
        return base_dir
    cat = category_for(filename)
    return os.path.join(base_dir, cat)
