import os, shutil, subprocess, sys

def find_ffmpeg():
    # 1) ffmpeg yang dibundel di samping aplikasi (paket .exe portable)
    try:
        from .paths import app_root
        for cand in (os.path.join(app_root(), "tools", "ffmpeg.exe"),
                     os.path.join(app_root(), "ffmpeg.exe")):
            if os.path.exists(cand):
                return cand
    except Exception:
        pass
    p = shutil.which("ffmpeg")
    if p:
        return p
    # FDM di PC pengguna membundel ffmpeg; pakai sebagai cadangan bila ada.
    candidates = [
        r"C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def convert(src, dst, on_done=None):
    """Konversi media (mis. mp4 -> mp3, mkv -> mp4) memakai ffmpeg. Blocking; panggil dari thread."""
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("ffmpeg tidak ditemukan di PATH.")
    if not os.path.exists(src):
        raise RuntimeError(f"Berkas sumber tidak ada: {src}")
    cmd = [ff, "-y", "-i", src]
    if dst.lower().endswith(".mp3"):
        cmd += ["-vn", "-codec:a", "libmp3lame", "-b:a", "256k"]
    cmd.append(dst)
    flags = 0
    if sys.platform.startswith("win"):
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "ffmpeg gagal")[-400:])
    if on_done:
        on_done(dst)
    return dst

def target_for(src, kind):
    base, _ = os.path.splitext(src)
    return base + (".mp3" if kind == "mp3" else ".mp4")
