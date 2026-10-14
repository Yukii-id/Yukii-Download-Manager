"""Dukungan YouTube berbasis yt-dlp (subproses, bukan impor).

Alasan subproses: yt-dlp yang diperbarui otomatis langsung berlaku untuk
unduhan berikutnya tanpa memulai ulang aplikasi, dan kerusakan yt-dlp tidak
menjatuhkan GUI. Progres dibaca dari --progress-template berciri khas "YDM|".
Pause = hentikan subproses; berkas .part/fragmen yt-dlp tetap di folder
sehingga resume (--continue bawaan) melanjutkan dari posisi terakhir.
"""
import json, os, re, subprocess, sys, threading, time
from collections import deque
from urllib.parse import urlparse

from .util import sanitize
from .converter import find_ffmpeg

_YT_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com",
             "music.youtube.com", "youtu.be", "www.youtu.be")

def is_youtube_url(url):
    if not url:
        return False
    try:
        host = (urlparse(url.strip()).hostname or "").lower()
    except Exception:
        return False
    return host in _YT_HOSTS

def quality_format(quality):
    """Petakan kualitas pilihan pengguna ke format selector yt-dlp."""
    q = str(quality or "720").lower()
    if q in ("audio", "mp3"):
        return "ba/b", True
    if q in ("best", "terbaik"):
        return "bv*+ba/b", False
    try:
        h = int(re.sub(r"\D", "", q) or 720)
    except ValueError:
        h = 720
    return f"bv*[height<={h}]+ba/b[height<={h}]", False

def ytdlp_base_cmd():
    """Urutan pilihan menjalankan yt-dlp:
    1) yt-dlp.exe mandiri di data/bin (hasil update otomatis versi .exe),
    2) bila aplikasi frozen (.exe): panggil diri sendiri lewat bootstrap --ytdlp,
    3) mode sumber: python -m yt_dlp.
    """
    from .paths import standalone_ytdlp_path, is_frozen
    standalone = standalone_ytdlp_path()
    if os.path.exists(standalone):
        return [standalone]
    if is_frozen():
        return [sys.executable, "--ytdlp"]
    return [sys.executable, "-m", "yt_dlp"]

def probe(url, cookies_from_browser="", fmt=None):
    """Ambil metadata video tanpa mengunduh.

    Bila fmt diberikan, hasil menyertakan total_est: jumlah ukuran format
    yang benar-benar akan diunduh (video + audio) dari requested_formats -
    dipakai sebagai penyebut progress bar sejak detik pertama.
    """
    cmd = ytdlp_base_cmd() + ["--dump-single-json", "--no-playlist", "--no-warnings"]
    if fmt:
        cmd += ["-f", fmt]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    cmd.append(url)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=90, creationflags=flags)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "yt-dlp probe gagal")[-400:])
    info = json.loads(r.stdout)
    heights = sorted({f.get("height") for f in info.get("formats", []) if f.get("height")}, reverse=True)
    total_est = 0
    req = info.get("requested_formats") or []
    if req:
        for f in req:
            total_est += int(f.get("filesize") or f.get("filesize_approx") or 0)
    if not total_est:
        total_est = int(info.get("filesize") or info.get("filesize_approx") or 0)
    return {
        "title": info.get("title") or "video-youtube",
        "duration": info.get("duration") or 0,
        "heights": heights,
        "id": info.get("id"),
        "total_est": total_est,
    }

_PROGRESS_RE = re.compile(r"^YDM\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)$")

def parse_progress_line(line):
    """Ubah satu baris template progres menjadi dict, atau None."""
    m = _PROGRESS_RE.match((line or "").strip())
    if not m:
        return None
    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None
    return {
        "downloaded": num(m.group(1)),
        "total": num(m.group(2)),
        "total_estimate": num(m.group(3)),
        "speed": num(m.group(4)),
        "status": m.group(5),
    }

class YoutubeJob:
    """Antarmuka sama seperti DownloadJob agar DownloadManager tidak berubah banyak."""
    def __init__(self, record, on_event=None, settings=None):
        self.rec = record
        self.id = record["id"]
        self.on_event = on_event or (lambda *a, **k: None)
        self.settings = settings
        self.stop_event = threading.Event()
        self.thread = None
        self.speed = 0.0
        self.segments_state = []
        self.logs = deque(maxlen=300)
        self._proc = None
        hdr = record.get("headers") or {}
        yt = hdr.get("youtube") or {}
        self.quality = yt.get("quality") or (settings.get("youtube_quality") if settings else None) or "720"
        self.cookies = (settings.get("youtube_cookies_from_browser") if settings else "") or ""

    def log(self, msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        self.logs.append(line)
        self.on_event("log", self.id, line)

    def pause(self):
        self.stop_event.set()
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def set_speed_limit(self, bps):
        self.rec["speed_limit"] = int(bps or 0)  # berlaku pada resume berikutnya

    def start(self):
        self.thread = threading.Thread(target=self._run, name=f"ydm-yt-{self.id}", daemon=True)
        self.thread.start()

    def _run(self):
        rec = self.rec
        url = rec["url"]
        try:
            self.on_event("status", self.id, "downloading")
            self.log(f"Memeriksa video: {url}")
            fmt, audio_only = quality_format(self.quality)
            info = probe(url, self.cookies, fmt=fmt)
            title = sanitize(info["title"])
            filename = f"{title}.mp3" if audio_only else f"{title}.mp4"
            total_est = int(info.get("total_est") or 0)
            self.on_event("meta", self.id, total_est if total_est > 0 else -1, filename)
            self.log(f"Judul: {info['title']} | kualitas: {self.quality} | format: {fmt} | estimasi total: {total_est} byte")
            os.makedirs(rec["save_dir"], exist_ok=True)
            outtmpl = os.path.join(rec["save_dir"], title + ".%(ext)s")

            cmd = ytdlp_base_cmd() + [
                # --progress WAJIB: tanpa ini yt-dlp membungkam progres saat
                # stdout-nya berupa pipe (bug "progres diam lalu 100%").
                "--newline", "--progress", "--no-warnings", "--no-playlist", "--continue",
                "--retries", "10", "--fragment-retries", "10",
                "-f", fmt, "-o", outtmpl,
                "--progress-template", "YDM|%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.status)s",
                "--print", "after_move:YDMFILE|%(filepath)s",
            ]
            if audio_only:
                cmd += ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
            else:
                cmd += ["--merge-output-format", "mp4"]
            ff = find_ffmpeg()
            if ff:
                cmd += ["--ffmpeg-location", ff]
            if self.cookies:
                cmd += ["--cookies-from-browser", self.cookies]
            limit = int(rec.get("speed_limit") or 0)
            if self.settings:
                limit = max(limit, int(self.settings.effective_global_limit_bps()))
            if limit > 0:
                cmd += ["--limit-rate", str(limit)]
            cmd.append(url)

            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          text=True, encoding="utf-8", errors="replace",
                                          creationflags=flags)
            downloaded = 0
            total = total_est if total_est > 0 else -1
            final_path = None
            last_lines = deque(maxlen=8)
            # Akumulasi antar-stream: yt-dlp mengunduh video lalu audio
            # sebagai dua aliran terpisah; downloaded_bytes mulai lagi
            # dari 0 pada aliran kedua. base_dl menampung aliran selesai.
            base_dl = 0
            cur_peak = 0
            stream_open = False
            for line in self._proc.stdout:
                if self.stop_event.is_set():
                    break
                line = line.rstrip("\n")
                if line.startswith("YDMFILE|"):
                    final_path = line[len("YDMFILE|"):].strip()
                    continue
                p = parse_progress_line(line)
                if p:
                    d = p["downloaded"]
                    t = p["total"] or p["total_estimate"]
                    if p["status"] == "finished":
                        if d is not None:
                            base_dl += int(d)
                        elif t:
                            base_dl += int(t)
                        cur_peak = 0
                        stream_open = False
                        downloaded = base_dl
                    elif d is not None:
                        if not stream_open:
                            stream_open = True
                            cur_peak = 0
                        if int(d) < cur_peak - 65536:
                            # aliran baru tanpa baris finished (jaga-jaga):
                            base_dl += cur_peak
                            cur_peak = 0
                        cur_peak = max(cur_peak, int(d))
                        downloaded = base_dl + int(d)
                        if t:
                            cand_total = base_dl + int(t)
                            if total <= 0 or cand_total > total:
                                total = cand_total
                    self.speed = p["speed"] or 0.0
                    if total > 0:
                        self.on_event("meta", self.id, total, os.path.basename(final_path) if final_path else filename)
                    self.on_event("progress", self.id, downloaded, self.speed, [])
                elif line.strip():
                    last_lines.append(line.strip())
            if self.stop_event.is_set():
                try:
                    self._proc.terminate()
                except Exception:
                    pass
                self._proc.wait(timeout=10)
                self.on_event("status", self.id, "paused", downloaded)
                self.log("Dijeda. Fragmen yt-dlp tersimpan; resume akan melanjutkan.")
                return
            rc = self._proc.wait()
            if rc != 0:
                raise RuntimeError("yt-dlp gagal: " + " / ".join(list(last_lines)[-2:])[:380])
            if final_path and os.path.exists(final_path):
                size = os.path.getsize(final_path)
                self.on_event("meta", self.id, size, os.path.basename(final_path))
                self.on_event("progress", self.id, size, 0.0, [])
                downloaded = size
            self.on_event("status", self.id, "completed", downloaded)
            self.log(f"Selesai: {final_path or filename}")
        except Exception as e:
            self.on_event("status", self.id, "error", 0, str(e))
            self.log(f"Error YouTube: {e}")
