import os, re, time
from urllib.parse import urlparse, unquote

def fmt_bytes(n):
    if n is None or n < 0:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:.0f} {u}" if f >= 100 or u == "B" else f"{f:.1f} {u}"
        f /= 1024.0

def fmt_speed(n):
    return fmt_bytes(n) + "/dtk" if n and n > 0 else "-"

def fmt_eta(seconds):
    if seconds is None or seconds < 0 or seconds == float("inf"):
        return "-"
    s = int(seconds)
    if s < 60:
        return f"{s} dtk"
    if s < 3600:
        return f"{s // 60} mnt {s % 60} dtk"
    return f"{s // 3600} jam {(s % 3600) // 60} mnt"

def filename_from_url(url, fallback="download"):
    try:
        p = urlparse(url)
        name = unquote(os.path.basename(p.path.rstrip("/")))
        if name and "." in name:
            return sanitize(name)
    except Exception:
        pass
    return fallback

def filename_from_disposition(cd):
    if not cd:
        return None
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.I)
    if m:
        return sanitize(unquote(m.group(1).strip(' "')))
    m = re.search(r'filename="?([^";]+)"?', cd, re.I)
    if m:
        return sanitize(m.group(1).strip())
    return None

_BAD = '<>:"/\\|?*'

def sanitize(name):
    out = "".join("_" if c in _BAD or ord(c) < 32 else c for c in name).strip(" .")
    return out[:180] or "download"

def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"

def is_url(text):
    return isinstance(text, str) and (text.startswith("http://") or text.startswith("https://") or text.startswith("ftp://"))

def is_magnet(text):
    return isinstance(text, str) and text.strip().lower().startswith("magnet:?")
