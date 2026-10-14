"""Engine unduhan multi-segmen (stdlib murni, tanpa Qt).

- Mendukung HTTP/HTTPS (urllib) dan FTP (urllib).
- Jika server mendukung Range dan ukuran diketahui, file dipecah menjadi N
  segmen, masing-masing disimpan ke berkas .seg<i>, lalu digabung saat selesai.
- Pause/resume: berkas segmen tidak dihapus saat jeda; resume melanjutkan
  dari ukuran berkas segmen yang ada.
- Pembatas kecepatan: token bucket global + per-unduhan.
"""
import os, threading, time, urllib.request, urllib.error
from collections import deque

from .util import filename_from_url, filename_from_disposition, unique_path

CHUNK = 64 * 1024

class TokenBucket:
    def __init__(self):
        self._lock = threading.Lock()
        self.limit = 0  # byte/dtk, 0 = tanpa batas
        self._tokens = 0.0
        self._last = time.monotonic()
    def set_limit(self, bps):
        with self._lock:
            self.limit = int(bps or 0)
            self._tokens = 0.0
            self._last = time.monotonic()
    def acquire(self, n, stop_event, extra_buckets=()):
        # extra_buckets: bucket tambahan (per-unduhan) dengan limit sendiri
        for b in (self,) + tuple(extra_buckets):
            if not b._acquire_one(n, stop_event):
                return False
        return True
    def _acquire_one(self, n, stop_event):
        while not stop_event.is_set():
            with self._lock:
                if self.limit <= 0:
                    return True
                now = time.monotonic()
                self._tokens = min(self.limit, self._tokens + (now - self._last) * self.limit)
                self._last = now
                if self._tokens >= n:
                    self._tokens -= n
                    return True
                need = (n - self._tokens) / self.limit
            stop_event.wait(min(need, 0.25))
        return False

GLOBAL_BUCKET = TokenBucket()

class ProbeResult:
    def __init__(self):
        self.total = -1
        self.accept_ranges = False
        self.filename = None
        self.error = None

def _opener_headers(headers):
    h = {"User-Agent": (headers or {}).get("User-Agent", "YDM/1.0")}
    for k, v in (headers or {}).items():
        if k.lower() not in ("range", "host"):
            h[k] = v
    return h

def probe(url, headers=None):
    """Minta header saja (Range: bytes=0-0) untuk tahu ukuran & dukungan resume."""
    res = ProbeResult()
    res.filename = filename_from_url(url)
    req = urllib.request.Request(url, headers={**_opener_headers(headers), "Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cd = r.headers.get("Content-Disposition")
            fn = filename_from_disposition(cd)
            if fn:
                res.filename = fn
            cr = r.headers.get("Content-Range")
            if r.status == 206 and cr and "/" in cr:
                try:
                    res.total = int(cr.rsplit("/", 1)[1])
                    res.accept_ranges = True
                except ValueError:
                    pass
            else:
                cl = r.headers.get("Content-Length")
                if cl:
                    res.total = int(cl)
                res.accept_ranges = (r.headers.get("Accept-Ranges", "").lower() == "bytes")
    except Exception as e:
        res.error = str(e)
    return res

class SegmentTask:
    def __init__(self, idx, start, end):
        self.idx, self.start, self.end = idx, start, end
        self.done = 0  # byte selesai di segmen ini (termasuk dari sesi sebelumnya)

class DownloadJob:
    def __init__(self, record, on_event=None):
        self.rec = record
        self.id = record["id"]
        self.on_event = on_event or (lambda *a, **k: None)
        self.stop_event = threading.Event()
        self.thread = None
        self.segments_state = []  # list [done_bytes_per_segment]
        self._bucket = TokenBucket()
        self._bucket.set_limit(record.get("speed_limit", 0))
        self._samples = deque(maxlen=240)
        self._last_bytes = 0
        self._last_t = time.monotonic()
        self.speed = 0.0
        self.logs = deque(maxlen=300)

    # ---------- util ----------
    def log(self, msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        self.logs.append(line)
        self.on_event("log", self.id, line)

    def _emit_progress(self, downloaded):
        now = time.monotonic()
        dt = now - self._last_t
        if dt >= 0.5:
            self.speed = (downloaded - self._last_bytes) / dt if dt > 0 else 0
            self._last_bytes = downloaded
            self._last_t = now
            self._samples.append((now, self.speed))
        self.on_event("progress", self.id, downloaded, self.speed, list(self.segments_state))

    def set_speed_limit(self, bps):
        self._bucket.set_limit(bps)

    def pause(self):
        self.stop_event.set()

    # ---------- utama ----------
    def start(self):
        self.thread = threading.Thread(target=self._run, name=f"ydm-dl-{self.id}", daemon=True)
        self.thread.start()

    def _seg_path(self, base, idx):
        return f"{base}.seg{idx}"

    def _run(self):
        rec = self.rec
        url = rec["url"]
        headers = rec.get("headers") or {}
        try:
            self.on_event("status", self.id, "downloading")
            self.log(f"Mulai: {url}")
            info = probe(url, headers)
            if info.error and info.total < 0:
                # beberapa server menolak Range tapi menerima GET biasa; coba lanjut single-stream
                self.log(f"Probe Range gagal ({info.error}); coba unduh aliran tunggal.")
                info.accept_ranges = False
            total = info.total if info.total >= 0 else int(rec.get("total", -1) or -1)
            filename = rec.get("filename") or info.filename or "download"
            if rec.get("filename") in (None, "", "download") and info.filename:
                filename = info.filename
            save_dir = rec["save_dir"]
            os.makedirs(save_dir, exist_ok=True)
            final = os.path.join(save_dir, filename)
            part_base = final + ".ydmpart"
            if os.path.exists(final) and not os.path.exists(part_base + ".seg0"):
                final = unique_path(final)
                part_base = final + ".ydmpart"
            self.on_event("meta", self.id, total, os.path.basename(final))

            nseg = int(rec.get("segments", 8) or 1)
            if not info.accept_ranges or total < 1024 * 1024:
                nseg = 1
            nseg = max(1, nseg)
            self.log(f"Ukuran: {total if total>0 else '?'} byte; segmen: {nseg}; resume didukung: {info.accept_ranges}")

            # bangun daftar segmen
            tasks = []
            if total > 0 and nseg > 1:
                step = total // nseg
                for i in range(nseg):
                    start = i * step
                    end = total - 1 if i == nseg - 1 else (i + 1) * step - 1
                    tasks.append(SegmentTask(i, start, end))
            else:
                tasks.append(SegmentTask(0, 0, total - 1 if total > 0 else -1))
            self.segments_state = [0] * len(tasks)
            for t in tasks:
                p = self._seg_path(part_base, t.idx)
                if os.path.exists(p):
                    sz = os.path.getsize(p)
                    want = (t.end - t.start + 1) if t.end >= 0 else sz
                    t.done = min(sz, want) if t.end >= 0 else sz
                self.segments_state[t.idx] = t.done
            downloaded0 = sum(self.segments_state)
            self._last_bytes = downloaded0
            self._emit_progress(downloaded0)

            errors = []
            def worker(task):
                try:
                    self._download_segment(url, headers, part_base, task)
                except Exception as e:
                    errors.append(f"segmen {task.idx}: {e}")

            threads = [threading.Thread(target=worker, args=(t,), daemon=True) for t in tasks]
            for th in threads:
                th.start()
            while any(th.is_alive() for th in threads):
                if self.stop_event.is_set():
                    break
                self._emit_progress(sum(self.segments_state))
                time.sleep(0.3)
            for th in threads:
                th.join(timeout=2)

            downloaded = sum(self.segments_state)
            if self.stop_event.is_set():
                self.on_event("status", self.id, "paused", downloaded)
                self.log("Dijeda. Progres segmen tersimpan untuk resume.")
                return
            if errors:
                raise RuntimeError("; ".join(errors[:3]))
            if total > 0 and downloaded < total:
                raise RuntimeError(f"Unduhan tidak lengkap: {downloaded}/{total} byte")

            # gabung segmen
            self.on_event("status", self.id, "merging", downloaded)
            self.log("Menggabungkan segmen...")
            with open(part_base + ".merged", "wb") as out:
                for t in tasks:
                    p = self._seg_path(part_base, t.idx)
                    with open(p, "rb") as f:
                        while True:
                            b = f.read(CHUNK)
                            if not b:
                                break
                            out.write(b)
            os.replace(part_base + ".merged", final)
            for t in tasks:
                p = self._seg_path(part_base, t.idx)
                if os.path.exists(p):
                    os.remove(p)
            self._emit_progress(downloaded)
            self.on_event("status", self.id, "completed", downloaded)
            self.log(f"Selesai: {final}")
        except Exception as e:
            self.on_event("status", self.id, "error", sum(self.segments_state), str(e))
            self.log(f"Error: {e}")

    def _download_segment(self, url, headers, part_base, task):
        path = self._seg_path(part_base, task.idx)
        want_total = (task.end - task.start + 1) if task.end >= 0 else -1
        attempt = 0
        while not self.stop_event.is_set():
            have = os.path.getsize(path) if os.path.exists(path) else 0
            task.done = have
            self.segments_state[task.idx] = have
            if want_total >= 0 and have >= want_total:
                return
            start = task.start + have
            h = dict(_opener_headers(headers))
            if task.end >= 0:
                h["Range"] = f"bytes={start}-{task.end}"
            attempt += 1
            try:
                req = urllib.request.Request(url, headers=h)
                with urllib.request.urlopen(req, timeout=30) as r:
                    if task.end >= 0 and have == 0 and task.start == 0 and r.status == 200 and want_total < 0:
                        pass  # aliran tunggal tanpa panjang diketahui
                    mode = "ab" if have > 0 else "wb"
                    # jika server mengabaikan Range (200) padahal kita minta lanjutan, tulis ulang
                    if h.get("Range") and r.status == 200 and have > 0:
                        mode = "wb"
                        task.done = 0
                    with open(path, mode) as f:
                        while not self.stop_event.is_set():
                            chunk = r.read(CHUNK)
                            if not chunk:
                                break
                            if not GLOBAL_BUCKET.acquire(len(chunk), self.stop_event, (self._bucket,)):
                                break
                            f.write(chunk)
                            task.done += len(chunk)
                            self.segments_state[task.idx] = task.done
                have = os.path.getsize(path) if os.path.exists(path) else 0
                task.done = have
                self.segments_state[task.idx] = have
                if want_total >= 0 and have < want_total and not self.stop_event.is_set():
                    raise IOError(f"koneksi terputus di {have}/{want_total}")
                return
            except Exception as e:
                if self.stop_event.is_set():
                    return
                if attempt >= 4:
                    raise
                self.log(f"Segmen {task.idx}: {e} — coba lagi ({attempt}/3)...")
                time.sleep(min(2 * attempt, 6))
