import os, queue, threading, time

from .db import Store
from .engine import DownloadJob, GLOBAL_BUCKET
from .torrent_engine import TorrentJob
from .categories import category_for, target_dir
from .util import filename_from_url, is_magnet
from .torrent_engine import parse_magnet_name
from .youtube import is_youtube_url, YoutubeJob

class DownloadManager:
    """Mengatur antrian, job aktif, dan persistensi status ke SQLite."""
    def __init__(self, store: Store, settings):
        self.store = store
        self.settings = settings
        self.jobs = {}               # id -> job
        self.events = queue.Queue()  # (kind, id, *args) dari thread job
        self._lock = threading.Lock()
        GLOBAL_BUCKET.set_limit(settings.effective_global_limit_bps())
        # unduhan yang tertinggal dalam status aktif saat aplikasi ditutup -> paused
        for r in store.all():
            if r["status"] in ("downloading", "merging"):
                store.update(r["id"], status="paused")

    # ---- event dari job ----
    def _on_event(self, kind, did, *args):
        self.events.put((kind, did, *args))
        if kind == "meta":
            total, filename = args
            self.store.update(did, total=total, filename=filename)
        elif kind == "progress":
            downloaded = args[0]
            self.store.update(did, downloaded=downloaded)
        elif kind == "status":
            status = args[0]
            kw = {"status": status}
            if len(args) > 1:
                kw["downloaded"] = args[1]
            if status == "error" and len(args) > 2:
                kw["error"] = args[2]
            if status == "completed":
                kw["finished_at"] = time.time()
                kw["error"] = ""
            self.store.update(did, **kw)

    # ---- CRUD ----
    def add(self, url, save_dir=None, filename=None, segments=None, headers=None,
            start_now=True, schedule_at=0, speed_limit=0, source="manual",
            youtube_quality=None):
        url = (url or "").strip()
        kind = "http"
        headers = dict(headers or {})
        if is_youtube_url(url):
            kind = "youtube"
            filename = "video-youtube.mp4"
            headers["youtube"] = {"quality": str(youtube_quality or self.settings.get("youtube_quality") or "720")}
        elif is_magnet(url) or url.lower().endswith(".torrent"):
            kind = "torrent"
            if is_magnet(url):
                filename = filename or parse_magnet_name(url)
            else:
                filename = filename or os.path.basename(url)
        else:
            filename = filename or filename_from_url(url)
        base_dir = save_dir or self.settings.get("download_dir")
        save_dir_final = target_dir(base_dir, filename, self.settings.get("smart_sort")) \
            if kind in ("http", "youtube") else base_dir
        rec = {
            "url": url, "kind": kind, "filename": filename, "save_dir": save_dir_final,
            "total": -1, "downloaded": 0,
            "status": "scheduled" if schedule_at else "queued",
            "segments": int(segments or self.settings.get("segments") or 8),
            "speed_limit": int(speed_limit or 0), "priority": 0,
            "category": category_for(filename), "tags": "",
            "headers": headers or {}, "schedule_at": float(schedule_at or 0),
            "error": "", "source": source,
        }
        did = self.store.add(rec)
        if start_now and not schedule_at:
            self.start(did)
        return did

    def start(self, did):
        with self._lock:
            if did in self.jobs:
                return
            rec = self.store.get(did)
            if not rec or rec["status"] == "completed":
                return
            active = sum(1 for j in self.jobs.values())
            maxc = int(self.settings.get("max_concurrent") or 3)
            if active >= maxc and rec["status"] == "queued":
                return  # tetap antri; dipromosikan saat ada slot kosong
            if rec["kind"] == "torrent":
                job = TorrentJob(rec, on_event=self._on_event)
            elif rec["kind"] == "youtube":
                job = YoutubeJob(rec, on_event=self._on_event, settings=self.settings)
            else:
                job = DownloadJob(rec, on_event=self._on_event)
            self.jobs[did] = job
        self.store.update(did, status="downloading", error="")
        job.start()

    def pause(self, did):
        with self._lock:
            job = self.jobs.pop(did, None)
        if job:
            job.pause()
        else:
            self.store.update(did, status="paused")

    def pause_all(self):
        for did in list(self.jobs.keys()):
            self.pause(did)

    def resume_all_paused(self):
        for r in self.store.all():
            if r["status"] in ("paused", "queued", "error"):
                self.start(r["id"])

    def delete(self, did, delete_file=False):
        self.pause(did)
        rec = self.store.get(did)
        if rec and delete_file:
            final = os.path.join(rec["save_dir"], rec["filename"])
            targets = [final] + [f"{final}.ydmpart.seg{i}" for i in range(32)]
            # sisa yt-dlp: .part, .ytdl, fragmen, berkas gabungan sementara
            import glob as _glob
            stem = os.path.splitext(rec["filename"])[0]
            for pat in (stem + ".part", stem + ".ytdl", stem + "*.part-Frag*",
                        stem + ".temp.*", stem + ".part.*"):
                targets += _glob.glob(os.path.join(rec["save_dir"], pat))
            for p in dict.fromkeys(targets):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except OSError:
                    pass
        self.store.delete(did)

    def poll(self):
        """Panggil berkala dari UI: promosikan antrian + cek jadwal."""
        # promosi antrian saat slot kosong
        with self._lock:
            active = len(self.jobs)
        maxc = int(self.settings.get("max_concurrent") or 3)
        if active < maxc:
            for r in self.store.all():
                if r["status"] == "queued":
                    self.start(r["id"])
                    break
        now = time.time()
        for r in self.store.all():
            if r["status"] == "scheduled" and r["schedule_at"] and r["schedule_at"] <= now:
                self.store.update(r["id"], status="queued", schedule_at=0)
                self.start(r["id"])
        # bersihkan job selesai dari dict aktif
        with self._lock:
            for did, job in list(self.jobs.items()):
                rec = self.store.get(did)
                if rec and rec["status"] in ("completed", "error", "paused") and job.thread and not job.thread.is_alive():
                    self.jobs.pop(did, None)

    def shutdown(self):
        """Jeda semua job, tunggu thread berhenti, lalu tutup database.

        Penting di Windows: berkas SQLite yang masih terbuka terkunci dan
        tidak bisa dihapus/dipindah.
        """
        with self._lock:
            jobs = list(self.jobs.values())
            self.jobs.clear()
        for job in jobs:
            job.pause()
        for job in jobs:
            if job.thread:
                job.thread.join(timeout=5)
        self.store.close()

    def job_for(self, did):
        return self.jobs.get(did)

    def apply_global_limit(self):
        GLOBAL_BUCKET.set_limit(self.settings.effective_global_limit_bps())
