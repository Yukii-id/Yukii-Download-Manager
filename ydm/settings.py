import json, os

DEFAULTS = {
    "download_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
    "segments": 8,
    "max_concurrent": 3,
    "global_limit_kbps": 0,          # 0 = tanpa batas
    "traffic_mode": "Tinggi",        # Rendah / Sedang / Tinggi (preset batas global)
    "smart_sort": True,
    "clipboard_watch": True,
    "close_to_tray": True,
    "drop_box": False,
    "compact_view": False,
    "theme": "Sistem",               # Sistem / Terang / Gelap
    "language": "id",                # id / en
    "confirm_download": True,        # popup konfirmasi sebelum unduhan baru dimulai
    "remote_enabled": False,
    "remote_port": 17654,
    "notify_done": True,
    "youtube_quality": "720",
    "youtube_cookies_from_browser": "",
    "auto_update_ytdlp": True,
}

TRAFFIC_PRESETS_KBPS = {"Rendah": 256, "Sedang": 2048, "Tinggi": 0}

class Settings:
    def __init__(self, path):
        self.path = path
        self.data = dict(DEFAULTS)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception:
                pass

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def effective_global_limit_bps(self):
        mode = self.get("traffic_mode")
        preset = TRAFFIC_PRESETS_KBPS.get(mode, 0)
        if preset:
            return preset * 1024
        kbps = int(self.get("global_limit_kbps") or 0)
        return kbps * 1024
