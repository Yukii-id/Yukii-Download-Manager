"""Update otomatis yt-dlp.

Kenapa perlu: YouTube mengubah sistemnya berkala dan yt-dlp merilis perbaikan
dengan cepat. Modul ini:
- mengecek versi terbaru di PyPI (sumber resmi pip),
- membandingkan dengan versi terpasang (importlib.metadata),
- bila lebih baru dan auto-update aktif: `pip install --upgrade yt-dlp`,
- mencatat status ke data/ytdlp_update.json (cek maks. sekali per 24 jam
  dari dalam aplikasi; skrip bat terjadwal bisa memaksa kapan pun).

Dipakai juga sebagai CLI untuk Task Scheduler:
  python -m ydm.updater --update-now     (cek + update bila ada)
  python -m ydm.updater --check          (cek saja, cetak JSON)
"""
import json, os, subprocess, sys, time, urllib.request
from importlib import metadata

PYPI_JSON = "https://pypi.org/pypi/yt-dlp/json"
CHECK_INTERVAL_SECONDS = 24 * 3600

def installed_version():
    try:
        return metadata.version("yt-dlp")
    except metadata.PackageNotFoundError:
        return None

def latest_version(timeout=20):
    req = urllib.request.Request(PYPI_JSON, headers={"User-Agent": "YDM-Updater/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["info"]["version"]

def _parse(v):
    parts = []
    for p in (v or "0").replace("-", ".").split("."):
        parts.append(int(p) if p.isdigit() else 0)
    return parts

def is_newer(latest, installed):
    if not installed:
        return True
    return _parse(latest) > _parse(installed)

def _state_path(data_dir):
    return os.path.join(data_dir, "ytdlp_update.json")

def load_state(data_dir):
    path = _state_path(data_dir)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(data_dir, state):
    os.makedirs(data_dir, exist_ok=True)
    with open(_state_path(data_dir), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def run_pip_upgrade(timeout=600):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                       capture_output=True, text=True, timeout=timeout, creationflags=flags)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "pip gagal")[-400:])
    return installed_version()

# ---------- mode .exe (frozen): tidak ada pip, pakai yt-dlp.exe mandiri ----------
def _is_frozen():
    return bool(getattr(sys, "frozen", False))

def _standalone_path(data_dir):
    from .paths import standalone_ytdlp_path
    return standalone_ytdlp_path(data_dir)

def _standalone_version(path):
    if not os.path.exists(path):
        return None
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
        r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=30,
                           creationflags=flags)
        v = (r.stdout or "").strip().splitlines()
        return v[0].strip() if v else None
    except Exception:
        return None

def download_standalone(latest, data_dir, timeout=300):
    """Unduh yt-dlp.exe resmi dari rilis GitHub yt-dlp (tag = versi PyPI)."""
    url = f"https://github.com/yt-dlp/yt-dlp/releases/download/{latest}/yt-dlp.exe"
    dest = _standalone_path(data_dir)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".new"
    req = urllib.request.Request(url, headers={"User-Agent": "YDM-Updater/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
    got = _standalone_version(tmp)
    if got != latest:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise RuntimeError(f"verifikasi yt-dlp.exe gagal: terunduh {got}, diharapkan {latest}")
    os.replace(tmp, dest)
    return got

def check_and_maybe_update(data_dir, auto_update=True, force=False, log=None):
    """Kembalikan dict hasil. Tidak melempar error jaringan ke pemanggil."""
    log = log or (lambda *a: None)
    state = load_state(data_dir)
    now = time.time()
    frozen = _is_frozen()
    if frozen:
        inst_before = _standalone_version(_standalone_path(data_dir)) or installed_version()
    else:
        inst_before = installed_version()
    result = {"installed": inst_before, "latest": None, "updated": False,
              "checked_at": now, "error": None, "mode": "exe" if frozen else "pip"}
    if not force and state.get("checked_at") and now - float(state["checked_at"]) < CHECK_INTERVAL_SECONDS:
        result["skipped"] = "sudah dicek < 24 jam lalu"
        result["latest"] = state.get("latest")
        return result
    try:
        latest = latest_version()
        result["latest"] = latest
        if is_newer(latest, inst_before):
            if auto_update:
                log(f"yt-dlp {latest} tersedia (terpasang {inst_before}); memperbarui...")
                newv = download_standalone(latest, data_dir) if frozen else run_pip_upgrade()
                result["updated"] = True
                result["installed"] = newv
                state["last_update_at"] = now
                state["last_update_to"] = newv
                log(f"yt-dlp diperbarui ke {newv}. Berlaku untuk unduhan berikutnya.")
            else:
                result["update_available"] = True
        state.update({"checked_at": now, "latest": latest,
                      "installed": result["installed"], "error": None})
    except Exception as e:
        result["error"] = str(e)
        state.update({"checked_at": now, "error": str(e)})
    save_state(data_dir, state)
    return result

def _main(argv):
    from .paths import data_dir as _dd
    data_dir = _dd()
    force = "--update-now" in argv or "--check" in argv
    auto = "--update-now" in argv
    res = check_and_maybe_update(data_dir, auto_update=auto, force=force,
                                 log=lambda m: print(m, flush=True))
    print(json.dumps(res, indent=2))
    return 0 if not res.get("error") else 1

if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
