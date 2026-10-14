"""Yukii Download Manager - aplikasi desktop (PySide6 / Qt6).

Jalankan:  python app.py            (GUI)
           python app.py --smoke    (tes: buka jendela offscreen lalu tutup)
"""
import json, os, subprocess, sys, time

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")

from ydm.db import Store
from ydm.settings import Settings
from ydm.manager import DownloadManager
from ydm.util import fmt_bytes, fmt_speed, fmt_eta, is_url, is_magnet
from ydm.remote_server import RemoteServer, load_or_create_token

SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
DB_PATH = os.path.join(DATA_DIR, "ydm.sqlite3")

STATUS_ID = {
    "queued": "Mengantri", "downloading": "Mengunduh", "paused": "Dijeda",
    "merging": "Menggabungkan", "completed": "Selesai", "error": "Error",
    "scheduled": "Terjadwal",
}
STATUS_EN = {
    "queued": "Queued", "downloading": "Downloading", "paused": "Paused",
    "merging": "Merging", "completed": "Completed", "error": "Error",
    "scheduled": "Scheduled",
}

# ---------- i18n: Bahasa Indonesia / English ----------
CUR_LANG = {"code": "id"}
LANG = {
    "id": {
        "add": "+ Tambah Unduhan", "batch": "Batch", "resume": "Lanjut", "pause": "Jeda",
        "delete": "Hapus", "settings_btn": "Pengaturan", "traffic_mode": "MODE TRAFIK",
        "search_ph": "Cari nama / URL...",
        "h_name": "NAMA UNIT", "h_size": "UKURAN", "h_prog": "PROGRES",
        "h_speed": "KECEPATAN", "h_eta": "SISA", "h_status": "STATUS",
        "tab_general": "UMUM", "tab_segments": "SEGMEN", "tab_speed": "KECEPATAN", "tab_log": "LOG",
        "segments_word": "SEGMEN",
        "confirm_title": "Mulai Unduhan?",
        "confirm_one": "Lanjutkan download file ini?\n\n{what}\n\nFolder tujuan: {dir}",
        "confirm_many": "Lanjutkan download {n} file?\n\nPertama: {what}\n\nFolder tujuan: {dir}",
        "yes": "Ya, Download", "no": "Batal",
        "f_all": "Semua", "f_downloading": "Mengunduh", "f_queued": "Mengantri",
        "f_paused": "Dijeda", "f_completed": "Selesai", "f_error": "Error",
        "m_resume": "▶ Lanjut / Resume", "m_pause": "⏸ Jeda", "m_open_file": "Buka File",
        "m_open_folder": "Buka Folder", "m_convert_mp3": "Konversi ke MP3 (ffmpeg)",
        "m_convert_mp4": "Konversi ke MP4 (ffmpeg)", "m_schedule": "Jadwalkan 1 jam lagi",
        "m_copy": "Salin URL", "m_del": "Hapus dari daftar", "m_del_file": "Hapus + berkas",
        "tray_show": "Tampilkan YDM", "tray_add": "Tambah unduhan...", "tray_exit": "Keluar",
        "tray_msg": "YDM tetap berjalan di tray. Klik kanan ikon tray untuk keluar.",
        "tray_done": "Unduhan selesai",
        "st_running": "berjalan", "st_queued": "antri", "st_mode": "Mode",
        "f_torrent": "Torrent", "f_youtube": "YouTube",
        "pick": "Pilih...", "pick_folder": "Pilih folder", "pick_dir_title": "Pilih folder unduhan",
        "graph_none": "Belum ada data kecepatan.", "graph_peak": "puncak",
        "skew_downloading": "mengunduh...",
        "add_title": "Tambah Unduhan",
        "url_ph": "https://... atau magnet:?xt=... atau path .torrent",
        "save_folder": "Folder simpan:", "filename": "Nama file:",
        "filename_ph": "(otomatis dari URL)", "segments_n": "Jumlah segmen:",
        "yt_quality": "Kualitas YouTube:",
        "yt_note": "Kolom kualitas hanya dipakai bila URL adalah YouTube.",
        "q_best": "Terbaik", "q_audio": "Audio MP3",
        "speed_limit": "Batas kecepatan:", "limit_suffix": " KB/dtk (0=tanpa batas)",
        "sched_start": "Jadwalkan mulai pada:",
        "batch_title": "Unduhan Batch - satu URL per baris (maks 100)",
        "pick_folder_btn": "Pilih folder...",
        "set_title": "Pengaturan YDM",
        "s_dir": "Folder unduhan:", "s_seg": "Segmen bawaan:",
        "s_conc": "Unduhan bersamaan maks:", "s_mode": "Mode trafik:",
        "mode_low": "Rendah", "mode_medium": "Sedang", "mode_high": "Tinggi",
        "s_smart": "Urutkan otomatis ke subfolder per kategori",
        "s_clip": "Pantau clipboard untuk URL/magnet",
        "s_tray": "Tombol tutup menyembunyikan ke tray",
        "s_compact": "Tampilan ringkas (baris pendek)",
        "s_drop": "Tampilkan drop box melayang",
        "s_theme": "Tema:", "theme_system": "Sistem", "theme_light": "Terang", "theme_dark": "Gelap",
        "s_lang": "Bahasa / Language:",
        "s_confirm": "Popup konfirmasi sebelum download dimulai",
        "s_startup": "Jalankan YDM otomatis saat Windows mulai (startup)",
        "s_ytq": "Kualitas YouTube bawaan:",
        "s_cookies": "Cookies YouTube dari browser:",
        "s_ytupd": "Update yt-dlp otomatis (cek harian dari PyPI)",
        "s_remote": "Aktifkan remote control lokal (127.0.0.1 saja)",
        "s_port": "Port remote:",
        "s_note": "Bahasa langsung berlaku tanpa mulai ulang. Remote berlaku setelah aplikasi dimulai ulang.",
        "tray_pause_all": "Jeda Semua",
        "d_name": "Nama", "d_url": "URL/Sumber", "d_folder": "Folder",
        "d_size": "Ukuran", "d_done": "Sudah", "d_status": "Status",
        "d_kind": "Jenis", "d_cat": "Kategori", "d_segplan": "Segmen direncanakan",
        "d_limit": "Batas", "d_nolimit": "tanpa batas", "d_sched": "Terjadwal",
        "conv_running": "Mengonversi ke {k} di latar...",
        "conv_done": "Konversi selesai: {p}", "conv_fail": "Konversi gagal: {e}",
        "remote_on": "Remote aktif di 127.0.0.1:{p} (token di data/remote_token.txt)",
        "ytdlp_updated": "yt-dlp diperbarui otomatis ke {v}.",
    },
    "en": {
        "add": "+ Add Download", "batch": "Batch", "resume": "Resume", "pause": "Pause",
        "delete": "Delete", "settings_btn": "Settings", "traffic_mode": "TRAFFIC MODE",
        "search_ph": "Search name / URL...",
        "h_name": "UNIT NAME", "h_size": "SIZE", "h_prog": "PROGRESS",
        "h_speed": "SPEED", "h_eta": "ETA", "h_status": "STATUS",
        "tab_general": "GENERAL", "tab_segments": "SEGMENTS", "tab_speed": "SPEED", "tab_log": "LOG",
        "segments_word": "SEGMENTS",
        "confirm_title": "Start Download?",
        "confirm_one": "Continue downloading this file?\n\n{what}\n\nSave to: {dir}",
        "confirm_many": "Continue downloading {n} files?\n\nFirst: {what}\n\nSave to: {dir}",
        "yes": "Yes, Download", "no": "Cancel",
        "f_all": "All", "f_downloading": "Downloading", "f_queued": "Queued",
        "f_paused": "Paused", "f_completed": "Completed", "f_error": "Error",
        "m_resume": "▶ Resume", "m_pause": "⏸ Pause", "m_open_file": "Open File",
        "m_open_folder": "Open Folder", "m_convert_mp3": "Convert to MP3 (ffmpeg)",
        "m_convert_mp4": "Convert to MP4 (ffmpeg)", "m_schedule": "Schedule in 1 hour",
        "m_copy": "Copy URL", "m_del": "Remove from list", "m_del_file": "Delete + file",
        "tray_show": "Show YDM", "tray_add": "Add download...", "tray_exit": "Exit",
        "tray_msg": "YDM keeps running in the tray. Right-click the tray icon to exit.",
        "tray_done": "Download finished",
        "st_running": "running", "st_queued": "queued", "st_mode": "Mode",
        "f_torrent": "Torrent", "f_youtube": "YouTube",
        "pick": "Browse...", "pick_folder": "Select folder", "pick_dir_title": "Select download folder",
        "graph_none": "No speed data yet.", "graph_peak": "peak",
        "skew_downloading": "downloading...",
        "add_title": "Add Download",
        "url_ph": "https://... or magnet:?xt=... or a .torrent path",
        "save_folder": "Save folder:", "filename": "File name:",
        "filename_ph": "(automatic from URL)", "segments_n": "Segments:",
        "yt_quality": "YouTube quality:",
        "yt_note": "The quality field only applies to YouTube URLs.",
        "q_best": "Best", "q_audio": "Audio MP3",
        "speed_limit": "Speed limit:", "limit_suffix": " KB/s (0=unlimited)",
        "sched_start": "Schedule start at:",
        "batch_title": "Batch Download - one URL per line (max 100)",
        "pick_folder_btn": "Browse folder...",
        "set_title": "YDM Settings",
        "s_dir": "Download folder:", "s_seg": "Default segments:",
        "s_conc": "Max simultaneous downloads:", "s_mode": "Traffic mode:",
        "mode_low": "Low", "mode_medium": "Medium", "mode_high": "High",
        "s_smart": "Auto-sort into category subfolders",
        "s_clip": "Watch clipboard for URLs/magnets",
        "s_tray": "Close button hides to tray",
        "s_compact": "Compact view (short rows)",
        "s_drop": "Show floating drop box",
        "s_theme": "Theme:", "theme_system": "System", "theme_light": "Light", "theme_dark": "Dark",
        "s_lang": "Bahasa / Language:",
        "s_confirm": "Confirmation popup before a download starts",
        "s_startup": "Start YDM automatically when Windows starts",
        "s_ytq": "Default YouTube quality:",
        "s_cookies": "YouTube cookies from browser:",
        "s_ytupd": "Automatic yt-dlp updates (daily check from PyPI)",
        "s_remote": "Enable local remote control (127.0.0.1 only)",
        "s_port": "Remote port:",
        "s_note": "Language applies immediately, no restart needed. Remote takes effect after restarting the app.",
        "tray_pause_all": "Pause All",
        "d_name": "Name", "d_url": "URL/Source", "d_folder": "Folder",
        "d_size": "Size", "d_done": "Downloaded", "d_status": "Status",
        "d_kind": "Type", "d_cat": "Category", "d_segplan": "Planned segments",
        "d_limit": "Limit", "d_nolimit": "unlimited", "d_sched": "Scheduled",
        "conv_running": "Converting to {k} in the background...",
        "conv_done": "Conversion finished: {p}", "conv_fail": "Conversion failed: {e}",
        "remote_on": "Remote active at 127.0.0.1:{p} (token in data/remote_token.txt)",
        "ytdlp_updated": "yt-dlp auto-updated to {v}.",
    },
}

def tr(key):
    return LANG.get(CUR_LANG["code"], LANG["id"]).get(key, LANG["id"].get(key, key))

def status_text(key):
    return (STATUS_EN if CUR_LANG["code"] == "en" else STATUS_ID).get(key, key)

# ---------- startup Windows (registri Run, per-user) ----------
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_startup_enabled():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY)
        winreg.QueryValueEx(k, "YDM")
        return True
    except Exception:
        return False

def set_startup_enabled(on):
    try:
        import winreg
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY)
        if on:
            if getattr(sys, "frozen", False):
                cmd = f'"{sys.executable}"'
            else:
                pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                exe = pyw if os.path.exists(pyw) else sys.executable
                cmd = f'"{exe}" "{os.path.join(BASE_DIR, "app.py")}"'
            winreg.SetValueEx(k, "YDM", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, "YDM")
            except FileNotFoundError:
                pass
        return True
    except Exception:
        return False


def asset_path(name):
    """Lokasi berkas aset (logo Gundam) - sumber: folder proyek; .exe: _MEIPASS."""
    for base in (getattr(sys, "_MEIPASS", None), BASE_DIR):
        if base:
            p = os.path.join(base, "assets", name)
            if os.path.exists(p):
                return p
    return None


def make_app_icon():
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon
    path = asset_path("gundam-head.png")
    if path:
        icon = QIcon()
        src = QPixmap(path)
        for s in (16, 24, 32, 48, 64, 128, 256):
            icon.addPixmap(src.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation))
        return icon
    pm = QPixmap(64, 64)
    pm.fill(QColor("#8f1220"))
    p = QPainter(pm)
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
    p.drawText(pm.rect(), 0x84, "Y")
    p.end()
    return QIcon(pm)


# ---------------- widget khusus ----------------
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt

# mode gelap aktif + palet gambar khusus (diisi apply_theme)
DARK_MODE = {"on": False}
PAL = {
    "seg_empty_top": "#3a1a21", "seg_empty_bot": "#241016", "seg_empty_pen": "#8a3a41",
    "seg_half_top": "#f0838c", "seg_half_bot": "#d21f2b", "seg_half_pen": "#d21f2b",
    "seg_full_top": "#f0c75e", "seg_full_bot": "#b97f16", "seg_full_pen": "#e8b13c",
    "graph_bg": "#1c0d12", "graph_line": "#ff5964", "graph_glow": (255, 89, 100, 70),
    "graph_text": "#e8b13c",
}

class SegmentsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.fractions = []
        self.setMinimumHeight(30)
    def set_data(self, fractions):
        self.fractions = fractions or []
        self.update()
    def paintEvent(self, e):
        from PySide6.QtGui import QLinearGradient
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        fr = self.fractions or [0.0] * 16
        n = len(fr)
        gap = 3
        bw = max(6, (w - gap * (n - 1)) // n)
        for i, f in enumerate(fr):
            x = i * (bw + gap)
            if f <= 0:
                top, bot = PAL["seg_empty_top"], PAL["seg_empty_bot"]
                pen = QColor(PAL["seg_empty_pen"])
            elif f < 1:
                top, bot = PAL["seg_half_top"], PAL["seg_half_bot"]
                pen = QColor(PAL["seg_half_pen"])
            else:
                top, bot = PAL["seg_full_top"], PAL["seg_full_bot"]
                pen = QColor(PAL["seg_full_pen"])
            g = QLinearGradient(0, 4, 0, h - 4)
            g.setColorAt(0, QColor(top)); g.setColorAt(1, QColor(bot))
            p.setPen(pen)
            p.setBrush(g)
            p.drawRoundedRect(x, 4, bw, h - 8, 3, 3)

class SpeedGraphWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.samples = []
        self.setMinimumHeight(60)
    def set_samples(self, samples):
        self.samples = list(samples)[-60:]
        self.update()
    def paintEvent(self, e):
        from PySide6.QtGui import QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(PAL["graph_bg"]))
        txt = QColor(PAL["graph_text"])
        if len(self.samples) < 2:
            p.setPen(txt)
            p.drawText(8, 20, tr("graph_none"))
            return
        mx = max(self.samples) or 1
        pts = []
        for i, s in enumerate(self.samples):
            x = i * w / 59
            y = h - 4 - (s / mx) * (h - 10)
            pts.append((x, y))
        # garis cahaya (glow) lalu garis inti - kesan 3D neon lembut
        glow = QPen(QColor(*PAL["graph_glow"])); glow.setWidth(5)
        core = QPen(QColor(PAL["graph_line"])); core.setWidth(2)
        for pen in (glow, core):
            p.setPen(pen)
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                p.drawLine(int(x1), int(y1), int(x2), int(y2))
        p.setPen(txt)
        p.drawText(8, 14, f"{tr('graph_peak')} {fmt_speed(mx)}")


# ---------------- dialog ----------------
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QDialogButtonBox, QFileDialog, QHBoxLayout, QPushButton,
    QPlainTextEdit, QCheckBox, QComboBox, QDateTimeEdit, QLabel)
from PySide6.QtCore import QDateTime

class AddDialog(QDialog):
    def __init__(self, parent, settings, prefill=""):
        super().__init__(parent)
        self.setWindowTitle(tr("add_title"))
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.url = QLineEdit(prefill)
        self.url.setPlaceholderText(tr("url_ph"))
        form.addRow("URL / Magnet:", self.url)
        row = QHBoxLayout()
        self.folder = QLineEdit(settings.get("download_dir"))
        btn = QPushButton(tr("pick"))
        btn.clicked.connect(self._pick)
        row.addWidget(self.folder); row.addWidget(btn)
        w = QWidget(); w.setLayout(row)
        form.addRow(tr("save_folder"), w)
        self.filename = QLineEdit()
        self.filename.setPlaceholderText(tr("filename_ph"))
        form.addRow(tr("filename"), self.filename)
        self.segments = QSpinBox(); self.segments.setRange(1, 32)
        self.segments.setValue(int(settings.get("segments")))
        form.addRow(tr("segments_n"), self.segments)
        self.yt_quality = QComboBox()
        self._qvals = ["1080", "720", "480", "360", "best", "audio"]
        self.yt_quality.addItems(["1080", "720", "480", "360", tr("q_best"), tr("q_audio")])
        cur = str(settings.get("youtube_quality") or "720")
        self.yt_quality.setCurrentIndex(self._qvals.index(cur) if cur in self._qvals else 1)
        form.addRow(tr("yt_quality"), self.yt_quality)
        lay_note = QLabel(tr("yt_note"))
        lay_note.setWordWrap(True)
        form.addRow(lay_note)
        self.limit = QSpinBox(); self.limit.setRange(0, 1024 * 1024)
        self.limit.setSuffix(tr("limit_suffix"))
        form.addRow(tr("speed_limit"), self.limit)
        self.sched_check = QCheckBox(tr("sched_start"))
        self.sched = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.sched.setCalendarPopup(True)
        form.addRow(self.sched_check, self.sched)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)
    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, tr("pick_folder"), self.folder.text())
        if d:
            self.folder.setText(d)
    def values(self):
        sched = self.sched.dateTime().toPython().timestamp() if self.sched_check.isChecked() else 0
        q = self._qvals[self.yt_quality.currentIndex()]
        return {
            "url": self.url.text().strip(),
            "save_dir": self.folder.text().strip() or None,
            "filename": self.filename.text().strip() or None,
            "segments": self.segments.value(),
            "speed_limit": self.limit.value() * 1024,
            "schedule_at": sched,
            "youtube_quality": q,
        }

class BatchDialog(QDialog):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.setWindowTitle(tr("batch_title"))
        self.setMinimumSize(560, 380)
        lay = QVBoxLayout(self)
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("https://contoh.com/file1.zip\nhttps://contoh.com/file2.iso")
        lay.addWidget(self.text)
        row = QHBoxLayout()
        self.folder = QLineEdit(settings.get("download_dir"))
        b = QPushButton(tr("pick_folder_btn")); b.clicked.connect(self._pick)
        row.addWidget(self.folder); row.addWidget(b)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)
    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, tr("pick_folder"), self.folder.text())
        if d:
            self.folder.setText(d)
    def urls(self):
        out = []
        for line in self.text.toPlainText().splitlines():
            line = line.strip()
            if line and (is_url(line) or is_magnet(line)):
                out.append(line)
        return out[:100], self.folder.text().strip() or None

class SettingsDialog(QDialog):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(tr("set_title"))
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        drow = QHBoxLayout()
        self.dir = QLineEdit(settings.get("download_dir"))
        dbtn = QPushButton(tr("pick"))
        dbtn.clicked.connect(self._pick_dir)
        drow.addWidget(self.dir); drow.addWidget(dbtn)
        dw = QWidget(); dw.setLayout(drow)
        form.addRow(tr("s_dir"), dw)
        self.seg = QSpinBox(); self.seg.setRange(1, 32); self.seg.setValue(int(settings.get("segments")))
        form.addRow(tr("s_seg"), self.seg)
        self.conc = QSpinBox(); self.conc.setRange(1, 10); self.conc.setValue(int(settings.get("max_concurrent")))
        form.addRow(tr("s_conc"), self.conc)
        self.mode = QComboBox()
        self._mode_vals = ["Rendah", "Sedang", "Tinggi"]
        self.mode.addItems([tr("mode_low"), tr("mode_medium"), tr("mode_high")])
        mv = settings.get("traffic_mode")
        self.mode.setCurrentIndex(self._mode_vals.index(mv) if mv in self._mode_vals else 1)
        form.addRow(tr("s_mode"), self.mode)
        self.smart = QCheckBox(tr("s_smart")); self.smart.setChecked(bool(settings.get("smart_sort")))
        form.addRow(self.smart)
        self.clip = QCheckBox(tr("s_clip")); self.clip.setChecked(bool(settings.get("clipboard_watch")))
        form.addRow(self.clip)
        self.tray = QCheckBox(tr("s_tray")); self.tray.setChecked(bool(settings.get("close_to_tray")))
        form.addRow(self.tray)
        self.compact = QCheckBox(tr("s_compact")); self.compact.setChecked(bool(settings.get("compact_view")))
        form.addRow(self.compact)
        self.drop = QCheckBox(tr("s_drop")); self.drop.setChecked(bool(settings.get("drop_box")))
        form.addRow(self.drop)
        self.theme = QComboBox()
        self._theme_vals = ["Sistem", "Terang", "Gelap"]
        self.theme.addItems([tr("theme_system"), tr("theme_light"), tr("theme_dark")])
        tv = settings.get("theme")
        self.theme.setCurrentIndex(self._theme_vals.index(tv) if tv in self._theme_vals else 0)
        form.addRow(tr("s_theme"), self.theme)
        self.lang = QComboBox(); self.lang.addItems(["Indonesia", "English"])
        self.lang.setCurrentText("English" if settings.get("language") == "en" else "Indonesia")
        form.addRow(tr("s_lang"), self.lang)
        self.confirm_dl = QCheckBox(tr("s_confirm"))
        self.confirm_dl.setChecked(bool(settings.get("confirm_download")))
        form.addRow(self.confirm_dl)
        self.startup = QCheckBox(tr("s_startup"))
        self.startup.setChecked(get_startup_enabled())
        form.addRow(self.startup)
        self.ytq = QComboBox()
        self._qvals = ["1080", "720", "480", "360", "best", "audio"]
        self.ytq.addItems(["1080", "720", "480", "360", tr("q_best"), tr("q_audio")])
        qv = str(settings.get("youtube_quality") or "720")
        self.ytq.setCurrentIndex(self._qvals.index(qv) if qv in self._qvals else 1)
        form.addRow(tr("s_ytq"), self.ytq)
        self.ytcookies = QComboBox(); self.ytcookies.addItems(["", "chrome", "edge", "firefox"])
        self.ytcookies.setCurrentText(settings.get("youtube_cookies_from_browser") or "")
        form.addRow(tr("s_cookies"), self.ytcookies)
        self.ytupd = QCheckBox(tr("s_ytupd"))
        self.ytupd.setChecked(bool(settings.get("auto_update_ytdlp")))
        form.addRow(self.ytupd)
        self.remote = QCheckBox(tr("s_remote"))
        self.remote.setChecked(bool(settings.get("remote_enabled"))); form.addRow(self.remote)
        self.port = QSpinBox(); self.port.setRange(1024, 65535); self.port.setValue(int(settings.get("remote_port")))
        form.addRow(tr("s_port"), self.port)
        lay.addLayout(form)
        note = QLabel(tr("s_note"))
        note.setWordWrap(True); lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save); bb.rejected.connect(self.reject)
        lay.addWidget(bb)
    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, tr("pick_dir_title"), self.dir.text())
        if d:
            self.dir.setText(d)
    def _save(self):
        s = self.settings
        s.set("download_dir", self.dir.text().strip())
        s.set("language", "en" if self.lang.currentText() == "English" else "id")
        s.set("confirm_download", self.confirm_dl.isChecked())
        set_startup_enabled(self.startup.isChecked())
        s.set("segments", self.seg.value())
        s.set("max_concurrent", self.conc.value())
        s.set("traffic_mode", self._mode_vals[self.mode.currentIndex()])
        s.set("smart_sort", self.smart.isChecked())
        s.set("clipboard_watch", self.clip.isChecked())
        s.set("close_to_tray", self.tray.isChecked())
        s.set("compact_view", self.compact.isChecked())
        s.set("drop_box", self.drop.isChecked())
        s.set("theme", self._theme_vals[self.theme.currentIndex()])
        s.set("remote_enabled", self.remote.isChecked())
        s.set("remote_port", self.port.value())
        s.set("youtube_quality", self._qvals[self.ytq.currentIndex()])
        s.set("youtube_cookies_from_browser", self.ytcookies.currentText())
        s.set("auto_update_ytdlp", self.ytupd.isChecked())
        self.accept()


# ---------------- jendela utama ----------------
from PySide6.QtWidgets import (QMainWindow, QToolBar, QTableWidget, QTableWidgetItem,
    QProgressBar, QTabWidget, QStatusBar, QSystemTrayIcon, QMenu, QMessageBox,
    QSplitter, QHeaderView, QApplication, QTextEdit, QStackedWidget, QFrame,
    QStyledItemDelegate, QButtonGroup, QStyleOptionViewItem)
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtCore import QTimer, Signal, QObject, QRectF, QEvent

FILTERS = ["Semua", "Mengunduh", "Mengantri", "Dijeda", "Selesai", "Error", "Torrent", "YouTube"]
_FILTER_KEY = {"Semua": "all", "Mengunduh": "downloading", "Mengantri": "queued",
               "Dijeda": "paused", "Selesai": "completed", "Error": "error"}

# ---------------- komponen gaya preview Gundam ----------------
def _chamfer_poly(r, cut=8):
    from PySide6.QtGui import QPolygonF
    from PySide6.QtCore import QPointF
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    return QPolygonF([QPointF(x + cut, y), QPointF(x + w, y), QPointF(x + w, y + h - cut),
                      QPointF(x + w - cut, y + h), QPointF(x, y + h), QPointF(x, y + cut)])


class ChamferButton(QPushButton):
    """Tombol sudut potong ala panel armor (digambar manual, gradasi 3D)."""
    def __init__(self, text="", primary=False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(32)

    def paintEvent(self, e):
        from PySide6.QtGui import QLinearGradient, QPen, QFont
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = DARK_MODE["on"]
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        down, hov = self.isDown(), self.underMouse()
        active = self.primary or (self.isCheckable() and self.isChecked())
        if not self.isEnabled():
            top, bot, edge, txt = "#6b5a5e", "#57484c", QColor("#4a3a3e"), QColor("#a89a9c")
        elif active:
            top, bot = ("#f04438", "#a31621") if hov and not down else ("#e02430", "#8f1220")
            if down:
                top, bot = "#8f1220", "#c8102e"
            edge, txt = QColor("#4d060d"), QColor("#ffffff")
        elif dark:
            top, bot = ("#52262e", "#2c1219") if hov else ("#40222a", "#241016")
            edge = QColor("#ff5964") if hov else QColor("#8a3a41")
            txt = QColor("#f6e9e4")
            if down:
                top, bot = bot, top
        else:
            top, bot = ("#ffffff", "#efc9ba") if hov else ("#ffffff", "#f3ddd2")
            edge = QColor("#d21f2b") if hov else QColor("#d9afa3")
            txt = QColor("#4a1218")
            if down:
                top, bot = bot, top
        g = QLinearGradient(0, r.top(), 0, r.bottom())
        g.setColorAt(0, QColor(top)); g.setColorAt(1, QColor(bot))
        p.setPen(QPen(edge, 1)); p.setBrush(g)
        p.drawPolygon(_chamfer_poly(r))
        p.setPen(QPen(QColor(255, 255, 255, 80 if (active or dark) else 170), 1))
        from PySide6.QtCore import QPointF
        p.drawLine(QPointF(r.x() + 8, r.y() + 1.5), QPointF(r.x() + r.width() - 1, r.y() + 1.5))
        p.setPen(txt)
        f = QFont(p.font()); f.setWeight(QFont.Weight.Bold if active else QFont.Weight.DemiBold)
        p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())


class SkewBar(QWidget):
    """Bilah progres miring (parallelogram) ala preview: gradasi merah ke emas + kilau."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pct = 0.0
        self.phase = 0
        self.indeterminate = False
        self.setMinimumHeight(19)

    def set_data(self, pct, phase, indeterminate=False):
        self.pct, self.phase, self.indeterminate = pct, phase, indeterminate
        self.update()

    def paintEvent(self, e):
        from PySide6.QtGui import QLinearGradient, QPen, QFont, QPolygonF
        from PySide6.QtCore import QPointF
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        skew = 7.0
        dark = DARK_MODE["on"]
        track = QPolygonF([QPointF(skew, 1), QPointF(w - 1, 1), QPointF(w - skew - 1, h - 1), QPointF(1, h - 1)])
        p.setPen(QPen(QColor("#8a3a41") if dark else QColor("#d9a08e"), 1))
        p.setBrush(QColor("#180a0e") if dark else QColor("#f7e3d7"))
        p.drawPolygon(track)
        frac = 0.4 if self.indeterminate else max(0.0, min(1.0, self.pct / 100.0))
        if frac > 0:
            tx2 = skew + (w - 1 - skew) * frac
            bx2 = 1 + (w - skew - 2) * frac
            fill = QPolygonF([QPointF(skew + 0.5, 2), QPointF(tx2, 2), QPointF(bx2, h - 2), QPointF(1.5, h - 2)])
            g = QLinearGradient(0, 0, w, 0)
            g.setColorAt(0, QColor("#8f1220")); g.setColorAt(0.55, QColor("#d21f2b")); g.setColorAt(1, QColor("#e8b13c"))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(g)
            p.drawPolygon(fill)
            # kilau bergerak (dipotong mengikuti bentuk isian)
            from PySide6.QtGui import QPainterPath
            sx = 2 + (w - 4) * (self.phase / 24.0)
            shine = QPolygonF([QPointF(sx, 2), QPointF(sx + 16, 2), QPointF(sx + 16 - skew + 2, h - 2), QPointF(sx - skew + 2, h - 2)])
            clip = QPainterPath(); clip.addPolygon(fill)
            p.setClipPath(clip)
            p.setBrush(QColor(255, 255, 255, 70))
            p.drawPolygon(shine)
            p.setClipping(False)
        txt = tr("skew_downloading") if self.indeterminate else f"{self.pct:.0f}%"
        f = QFont("Segoe UI", 9); f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(QColor(0, 0, 0, 150))
        p.drawText(QRectF(1, 1, w, h), Qt.AlignmentFlag.AlignCenter, txt)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, txt)


class NameDelegate(QStyledItemDelegate):
    """Sel nama dua baris ala preview: nama tebal + baris meta kecil."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def paint(self, painter, option, index):
        from PySide6.QtWidgets import QStyle
        from PySide6.QtGui import QFont
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        widget = option.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)
        did = index.data(Qt.ItemDataRole.UserRole)
        name = index.data(Qt.ItemDataRole.UserRole + 1) or ""
        meta = self.win._meta_by_id.get(did, "")
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        dark = DARK_MODE["on"]
        name_col = QColor("#ffffff") if selected else QColor("#f6e9e4" if dark else "#33161c")
        meta_col = QColor("#ffd9c9") if selected else QColor("#c09a92" if dark else "#a08a84")
        rect = option.rect.adjusted(10, 5, -6, -5)
        painter.save()
        f1 = QFont("Segoe UI", 10); f1.setWeight(QFont.Weight.Bold)
        painter.setFont(f1); painter.setPen(name_col)
        painter.drawText(QRectF(rect.x(), rect.y(), rect.width(), rect.height() / 2),
                         Qt.AlignmentFlag.AlignVCenter, name)
        f2 = QFont("Consolas", 8)
        painter.setFont(f2); painter.setPen(meta_col)
        painter.drawText(QRectF(rect.x(), rect.y() + rect.height() / 2, rect.width(), rect.height() / 2),
                         Qt.AlignmentFlag.AlignVCenter, meta)
        painter.restore()


class StatusDelegate(QStyledItemDelegate):
    """Sel status sebagai chip berwarna ala HUD preview."""
    COLORS = {
        "downloading": ("#d21f2b", "#ffffff"), "merging": ("#e07b39", "#ffffff"),
        "completed": ("#37d67a", "#0c3822"), "paused": ("#ffb020", "#4d3400"),
        "queued": (None, None), "scheduled": ("#5b7189", "#ffffff"),
        "error": ("#5e0a12", "#ff8f9a"),
    }

    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def paint(self, painter, option, index):
        from PySide6.QtWidgets import QStyle
        from PySide6.QtGui import QFont, QPen
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        widget = option.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)
        key = index.data(Qt.ItemDataRole.UserRole + 1) or ""
        label = (status_text(key) or "").upper()
        dark = DARK_MODE["on"]
        bg, fg = self.COLORS.get(key, (None, None))
        painter.save()
        f = QFont("Consolas", 8); f.setWeight(QFont.Weight.Bold)
        painter.setFont(f)
        tw = painter.fontMetrics().horizontalAdvance(label) + 18
        rect = QRectF(option.rect.center().x() - tw / 2, option.rect.center().y() - 10, tw, 20)
        if bg:
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(bg))
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(QColor(fg))
        else:
            painter.setPen(QPen(QColor("#8a3a41") if dark else QColor("#d9a08e"), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(QColor("#c09a92") if dark else QColor("#a08a84"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()


class MainWindow(QMainWindow):
    def __init__(self, settings, store, manager):
        super().__init__()
        self.settings, self.store, self.manager = settings, store, manager
        self.setWindowTitle("Yukii Download Manager")
        # jendela tanpa bingkai OS: kartu melayang seperti poster preview
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1104, 704)
        self.setMinimumSize(924, 584)
        self.setAcceptDrops(True)
        self.filter_name = "Semua"
        self.search_text = ""
        self.seg_fractions = {}
        self.speed_hist = {}
        self.logs_by_id = {}
        self._last_clip = ""
        self.remote = None
        self._ytdlp_msg = None
        self._anim_phase = 0
        self._faded = False
        self._glow_anim = None
        self._rows_by_id = {}
        self._meta_by_id = {}
        self._drag_widgets = []
        self._drag_offset = None
        self._checked_ids = set()
        self._visible_ids = []
        self._refreshing = False
        self._build_ui()
        self._apply_3d_effects()
        self._build_tray()
        self._start_timers()
        self._maybe_remote()
        self._start_ytdlp_autoupdate()
        self.refresh()

    def _start_ytdlp_autoupdate(self):
        if not self.settings.get("auto_update_ytdlp"):
            return
        import threading
        from ydm.updater import check_and_maybe_update
        def run():
            try:
                res = check_and_maybe_update(DATA_DIR, auto_update=True)
                if res.get("updated"):
                    self._ytdlp_msg = tr("ytdlp_updated").format(v=res.get('installed'))
                elif res.get("error"):
                    self._ytdlp_msg = None
            except Exception:
                pass
        threading.Thread(target=run, daemon=True, name="ydm-ytdlp-update").start()

    # ---------- UI ----------
    def _build_ui(self):
        # panggung transparan -> kartu utama melayang dengan bayangan (gaya poster preview)
        stage = QWidget(); stage.setObjectName("stage")
        self.setCentralWidget(stage)
        self.stage = stage
        stage.installEventFilter(self)
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(12, 12, 12, 12)
        self._stage_layout = stage_layout
        card = QFrame(); card.setObjectName("card")
        self.card = card
        stage_layout.addWidget(card)
        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._lpath = asset_path("gundam-head.png")

        # ---- pita judul khusus: logo Gundam + nama + tombol jendela ----
        header = QWidget(); header.setObjectName("gundamHeader")
        self.header = header
        hrow = QHBoxLayout(header); hrow.setContentsMargins(14, 7, 10, 7)
        logo = QLabel()
        if self._lpath:
            from PySide6.QtGui import QPixmap
            logo.setPixmap(QPixmap(self._lpath).scaledToHeight(54, Qt.TransformationMode.SmoothTransformation))
        hrow.addWidget(logo)
        tbox = QVBoxLayout()
        gtitle = QLabel('YUKII <span style="color:#ff5964">DOWNLOAD</span> MANAGER')
        gtitle.setObjectName("gundamTitle")
        gsub = QLabel("MECHA-OS · MOBILE SUIT DOWNLOAD SYSTEM")
        gsub.setObjectName("gundamSub")
        tbox.addWidget(gtitle); tbox.addWidget(gsub)
        hrow.addLayout(tbox)
        hrow.addStretch(1)
        self.btn_min = QPushButton("─"); self.btn_min.setObjectName("winBtn")
        self.btn_max = QPushButton("▢"); self.btn_max.setObjectName("winBtn")
        self.btn_close = QPushButton("✕"); self.btn_close.setObjectName("winClose")
        for b in (self.btn_min, self.btn_max, self.btn_close):
            b.setFixedSize(36, 24)
            hrow.addWidget(b)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max)
        self.btn_close.clicked.connect(self.close)
        root.addWidget(header)
        self._drag_widgets = [header, logo, gtitle, gsub]
        for w in self._drag_widgets:
            w.installEventFilter(self)

        # ---- bilah alat: tombol chamfer + chip mode trafik ----
        toolbar = QWidget(); toolbar.setObjectName("toolbarRow")
        self.toolbar = toolbar
        trow = QHBoxLayout(toolbar); trow.setContentsMargins(14, 10, 14, 10); trow.setSpacing(8)
        self.btn_add = ChamferButton("＋ " + tr("add"), primary=True); self.btn_add.clicked.connect(self.on_add)
        self.btn_batch = ChamferButton(tr("batch")); self.btn_batch.clicked.connect(self.on_batch)
        self.btn_resume = ChamferButton("▶ " + tr("resume")); self.btn_resume.clicked.connect(self.on_resume_sel)
        self.btn_pause = ChamferButton("⏸ " + tr("pause")); self.btn_pause.clicked.connect(self.on_pause_sel)
        self.btn_del = ChamferButton(tr("delete")); self.btn_del.clicked.connect(self.on_delete_sel)
        self.btn_settings = ChamferButton(tr("settings_btn")); self.btn_settings.clicked.connect(self.on_settings)
        for b in (self.btn_add, self.btn_batch, self.btn_resume, self.btn_pause, self.btn_del, self.btn_settings):
            trow.addWidget(b)
        trow.addStretch(1)
        self.mode_chip = QLabel(); self.mode_chip.setObjectName("gundamChip")
        self._update_mode_chip()
        trow.addWidget(self.mode_chip)
        root.addWidget(toolbar)
        # ---- badan kartu (ada bantalan sisi seperti poster) ----
        body = QWidget(); body.setObjectName("bodyPad")
        bl = QVBoxLayout(body); bl.setContentsMargins(14, 8, 14, 10); bl.setSpacing(8)
        root.addWidget(body, 1)
        # bilah filter + cari
        frow = QHBoxLayout()
        self.filter_btns = {}
        for name in FILTERS:
            b = QPushButton(tr("f_" + _FILTER_KEY.get(name, name.lower()))); b.setCheckable(True); b.setObjectName("pill")
            b.clicked.connect(lambda _=False, n=name: self.set_filter(n))
            self.filter_btns[name] = b
            frow.addWidget(b)
        self.filter_btns["Semua"].setChecked(True)
        frow.addStretch(1)
        self.search = QLineEdit(); self.search.setPlaceholderText(tr("search_ph"))
        self.search.setMinimumWidth(210)
        self.search.textChanged.connect(lambda t: setattr(self, "search_text", t) or self.refresh())
        frow.addWidget(self.search)
        bl.addLayout(frow)

        split = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["☐", tr("h_name"), tr("h_size"), tr("h_prog"),
                                              tr("h_speed"), tr("h_eta"), tr("h_status")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 36)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 190)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 128)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_select)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_context_menu)
        self.table.doubleClicked.connect(lambda *_: self.open_file())
        self.table.setItemDelegateForColumn(1, NameDelegate(self))
        self.table.setItemDelegateForColumn(6, StatusDelegate(self))
        self.table.installEventFilter(self)
        # watermark kepala Gundam samar di sudut kanan bawah tabel (seperti poster)
        self._wm = QLabel(self.table.viewport())
        self._wm.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if self._lpath:
            from PySide6.QtGui import QPixmap
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            self._wm.setPixmap(QPixmap(self._lpath).scaledToWidth(230, Qt.TransformationMode.SmoothTransformation))
            _op = QGraphicsOpacityEffect(self._wm); _op.setOpacity(0.08)
            self._wm.setGraphicsEffect(_op)
        split.addWidget(self.table)

        # panel bawah: tab trapesium (tombol chamfer) + tumpukan halaman
        panel = QWidget(); panel.setObjectName("panelBox")
        pl = QVBoxLayout(panel); pl.setContentsMargins(0, 0, 0, 0); pl.setSpacing(0)
        tabrow = QHBoxLayout(); tabrow.setContentsMargins(8, 6, 8, 0); tabrow.setSpacing(4)
        self.tab_btns = {}
        self._tab_group = QButtonGroup(self); self._tab_group.setExclusive(True)
        for i, name in enumerate([tr("tab_general"), tr("tab_segments"), tr("tab_speed"), tr("tab_log")]):
            b = ChamferButton(name); b.setCheckable(True)
            b.clicked.connect(lambda _=False, ix=i: self.pages.setCurrentIndex(ix))
            self._tab_group.addButton(b)
            self.tab_btns[i] = b
            tabrow.addWidget(b)
        self.tab_btns[0].setChecked(True)
        tabrow.addStretch(1)
        pl.addLayout(tabrow)
        self.pages = QStackedWidget(); self.tabs = self.pages
        self.detail = QTextEdit(); self.detail.setReadOnly(True); self.detail.setObjectName("tabPage")
        self.pages.addWidget(self.detail)
        self.seg_widget = SegmentsWidget(); self.seg_widget.setObjectName("tabPage")
        self.pages.addWidget(self.seg_widget)
        self.graph = SpeedGraphWidget(); self.graph.setObjectName("tabPage")
        self.pages.addWidget(self.graph)
        self.log_view = QPlainTextEdit(); self.log_view.setReadOnly(True); self.log_view.setObjectName("tabPage")
        self.pages.addWidget(self.log_view)
        pl.addWidget(self.pages)
        split.addWidget(panel)
        split.setSizes([430, 210])
        bl.addWidget(split, 1)

        # bilah status: pita gelap ala HUD dengan titik hijau + label kanan emas
        sband = QWidget(); sband.setObjectName("statusBand")
        srow = QHBoxLayout(sband); srow.setContentsMargins(12, 5, 12, 5)
        self.status_dot = QLabel("●"); self.status_dot.setObjectName("statusDot")
        self.status_label = QLabel("Siap"); self.status_label.setObjectName("statusText")
        self.status_right = QLabel("YDM — RED COMET BUILD"); self.status_right.setObjectName("statusRight")
        srow.addWidget(self.status_dot); srow.addWidget(self.status_label)
        srow.addStretch(1); srow.addWidget(self.status_right)
        bl.addWidget(sband)

    # ---------- krom jendela khusus ----------
    def _update_mode_chip(self):
        _mk = {"Rendah": "mode_low", "Sedang": "mode_medium", "Tinggi": "mode_high"}
        _mv = str(self.settings.get('traffic_mode'))
        _disp = tr(_mk[_mv]) if _mv in _mk else _mv
        self.mode_chip.setText(f"{tr('traffic_mode')}: {_disp.upper()}")

    def _status(self, msg):
        self.status_label.setText(msg)

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.Type.WindowStateChange and hasattr(self, "_stage_layout"):
            maxi = self.isMaximized()
            self._stage_layout.setContentsMargins(0, 0, 0, 0) if maxi else self._stage_layout.setContentsMargins(12, 12, 12, 12)
            self.card.setProperty("maxi", maxi)
            self.card.style().unpolish(self.card); self.card.style().polish(self.card)

    def eventFilter(self, obj, ev):
        t = ev.type()
        if obj is getattr(self, "table", None) and t == QEvent.Type.Resize:
            self._place_watermark()
        if obj is getattr(self, "stage", None) and t == QEvent.Type.MouseButtonPress \
                and ev.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            # cincin margin 12px di sekeliling kartu = zona ubah ukuran jendela
            gp = ev.globalPosition().toPoint()
            r = self.frameGeometry()
            edges = Qt.Edge(0)
            if gp.x() - r.x() <= 11:
                edges |= Qt.Edge.LeftEdge
            if r.x() + r.width() - gp.x() <= 11:
                edges |= Qt.Edge.RightEdge
            if gp.y() - r.y() <= 11:
                edges |= Qt.Edge.TopEdge
            if r.y() + r.height() - gp.y() <= 11:
                edges |= Qt.Edge.BottomEdge
            if edges:
                wh = self.windowHandle()
                if wh is not None and wh.startSystemResize(edges):
                    return True
        if obj in getattr(self, "_drag_widgets", []):
            if t == QEvent.Type.MouseButtonDblClick and ev.button() == Qt.MouseButton.LeftButton:
                self._toggle_max()
                return True
            if t == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
                wh = self.windowHandle()
                if wh is not None and wh.startSystemMove():
                    return True
                # cadangan: geser manual bila startSystemMove tak tersedia
                self._drag_offset = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if t == QEvent.Type.MouseMove and getattr(self, "_drag_offset", None) is not None:
                if ev.buttons() & Qt.MouseButton.LeftButton and not self.isMaximized():
                    self.move(ev.globalPosition().toPoint() - self._drag_offset)
                return True
            if t == QEvent.Type.MouseButtonRelease:
                self._drag_offset = None
        return super().eventFilter(obj, ev)

    def _place_watermark(self):
        if not hasattr(self, "_wm"):
            return
        vp = self.table.viewport()
        self._wm.move(vp.width() - 175, vp.height() - 195)
        self._wm.resize(230, 243)

    def _apply_3d_effects(self):
        """Bayangan kartu melayang + cahaya bernapas di tombol utama."""
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        dark = DARK_MODE["on"]
        eff = QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(28); eff.setOffset(0, 8)
        eff.setColor(QColor(0, 0, 0, 190) if dark else QColor(90, 15, 25, 90))
        self.card.setGraphicsEffect(eff)
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(16); glow.setOffset(0, 2)
        glow.setColor(QColor(255, 60, 80, 200))
        self.btn_add.setGraphicsEffect(glow)
        if self._glow_anim is not None:
            self._glow_anim.stop()
        anim = QPropertyAnimation(glow, b"blurRadius", self)
        anim.setStartValue(13.0); anim.setEndValue(30.0)
        anim.setDuration(1500)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.setLoopCount(-1)
        anim.start()
        self._glow_anim = anim

    def showEvent(self, e):
        super().showEvent(e)
        if not self._faded:
            self._faded = True
            from PySide6.QtCore import QPropertyAnimation, QEasingCurve
            anim = QPropertyAnimation(self, b"windowOpacity", self)
            anim.setStartValue(0.0); anim.setEndValue(1.0)
            anim.setDuration(300)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            self._fade_anim = anim

    def retranslate(self):
        """Terapkan bahasa aktif ke seluruh teks jendela utama saat itu juga."""
        self.btn_add.setText("＋ " + tr("add"))
        self.btn_batch.setText(tr("batch"))
        self.btn_resume.setText("▶ " + tr("resume"))
        self.btn_pause.setText("⏸ " + tr("pause"))
        self.btn_del.setText(tr("delete"))
        self.btn_settings.setText(tr("settings_btn"))
        for name, b in self.filter_btns.items():
            b.setText(tr("f_" + _FILTER_KEY.get(name, name.lower())))
        self.search.setPlaceholderText(tr("search_ph"))
        for i, key in enumerate(["tab_general", "tab_segments", "tab_speed", "tab_log"]):
            self.tab_btns[i].setText(tr(key))
        glyph = "☑" if self._visible_ids and all(
            d in self._checked_ids for d in self._visible_ids) else "☐"
        self.table.setHorizontalHeaderLabels(
            [glyph, tr("h_name"), tr("h_size"), tr("h_prog"),
             tr("h_speed"), tr("h_eta"), tr("h_status")])
        self._update_mode_chip()
        if hasattr(self, "tray"):
            self._build_tray_menu()
        self.refresh()
        if self.selected_ids():
            self.on_select()

    def _build_tray(self):
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        self._build_tray_menu()
        self.tray.activated.connect(lambda r: self.showNormal() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _build_tray_menu(self):
        menu = QMenu()
        menu.addAction(tr("tray_show"), self.showNormal)
        menu.addAction(tr("tray_add"), self.on_add)
        menu.addAction(tr("tray_pause_all"), self.manager.pause_all)
        menu.addAction(tr("tray_exit"), QApplication.instance().quit)
        self.tray.setContextMenu(menu)

    def _start_timers(self):
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(600)
        clip = QGuiApplication.clipboard()
        clip.dataChanged.connect(self.on_clipboard)

    def _maybe_remote(self):
        if self.settings.get("remote_enabled"):
            token = load_or_create_token(DATA_DIR)
            self.remote = RemoteServer(int(self.settings.get("remote_port")), token,
                list_fn=lambda: [{"id": r["id"], "filename": r["filename"], "status": r["status"],
                                  "downloaded": r["downloaded"], "total": r["total"]} for r in self.store.all()],
                add_fn=lambda url: self.manager.add(url))
            self.remote.start()
            self._status(tr("remote_on").format(p=self.settings.get('remote_port')))

    # ---------- filter & refresh ----------
    def set_filter(self, name):
        self.filter_name = name
        for n, b in self.filter_btns.items():
            b.setChecked(n == name)
        self.refresh()

    def _visible_rows(self):
        rows = self.store.all()
        out = []
        for r in rows:
            if self.search_text and self.search_text.lower() not in r["filename"].lower():
                continue
            f = self.filter_name
            if f == "Mengunduh" and r["status"] not in ("downloading", "merging"):
                continue
            if f == "Mengantri" and r["status"] not in ("queued", "scheduled"):
                continue
            if f == "Dijeda" and r["status"] != "paused":
                continue
            if f == "Selesai" and r["status"] != "completed":
                continue
            if f == "Error" and r["status"] != "error":
                continue
            if f == "Torrent" and r["kind"] != "torrent":
                continue
            if f == "YouTube" and r["kind"] != "youtube":
                continue
            out.append(r)
        return out

    def refresh(self):
        from PySide6.QtGui import QFont
        from urllib.parse import urlparse
        self._refreshing = True
        rows = self._visible_rows()
        self._rows_by_id = {r["id"]: r for r in rows}
        self._visible_ids = [r["id"] for r in rows]
        self.table.setRowCount(len(rows))
        compact = bool(self.settings.get("compact_view"))
        num_font = QFont("Consolas", 10)
        for i, r in enumerate(rows):
            job = self.manager.job_for(r["id"])
            speed = job.speed if job else 0
            pct = (r["downloaded"] / r["total"] * 100) if r["total"] > 0 else (100 if r["status"] == "completed" else 0)
            eta = ((r["total"] - r["downloaded"]) / speed) if speed > 0 and r["total"] > 0 else None
            host = urlparse(r["url"]).netloc or r["kind"].upper()
            self._meta_by_id[r["id"]] = (
                f"{host} · {r['segments']} {tr('segments_word')} · {fmt_bytes(r['downloaded'])} / {fmt_bytes(r['total'])}")
            # kolom 0: centang (select)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if r["id"] in self._checked_ids
                              else Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, r["id"])
            self.table.setItem(i, 0, chk)
            # kolom 1: nama (digambar delegate dua baris)
            item = QTableWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, r["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, r["filename"])
            self.table.setItem(i, 1, item)
            # kolom 2,4,5: angka Consolas
            for c, v in ((2, fmt_bytes(r["total"])),
                         (4, fmt_speed(speed) if r["status"] == "downloading" else "-"),
                         (5, fmt_eta(eta))):
                it = QTableWidgetItem(str(v)); it.setFont(num_font)
                it.setData(Qt.ItemDataRole.UserRole, r["id"])
                self.table.setItem(i, c, it)
            # kolom 3: bilah progres miring
            bar = SkewBar()
            if r["status"] in ("downloading", "merging") and r["total"] <= 0:
                bar.set_data(0, self._anim_phase, indeterminate=True)
            else:
                bar.set_data(pct, self._anim_phase)
            self.table.setCellWidget(i, 3, bar)
            # kolom 6: status (digambar delegate sebagai chip)
            sit = QTableWidgetItem("")
            sit.setData(Qt.ItemDataRole.UserRole, r["id"])
            sit.setData(Qt.ItemDataRole.UserRole + 1, r["status"])
            self.table.setItem(i, 6, sit)
            self.table.setRowHeight(i, 36 if compact else 52)
        self._refreshing = False
        self._update_statusbar(rows)

    def _update_statusbar(self, rows=None):
        rows = rows if rows is not None else self.store.all()
        total_speed = sum((self.manager.job_for(r["id"]).speed if self.manager.job_for(r["id"]) else 0)
                          for r in rows if r["status"] == "downloading")
        active = sum(1 for r in rows if r["status"] == "downloading")
        queued = sum(1 for r in rows if r["status"] in ("queued", "scheduled"))
        self._status(f"▼ {fmt_speed(total_speed)}   ·   {active} {tr('st_running')} · {queued} {tr('st_queued')} · {tr('st_mode')}: {self.settings.get('traffic_mode')}")

    def selected_ids(self):
        if self._checked_ids:
            vis = [d for d in self._visible_ids if d in self._checked_ids]
            return vis or sorted(self._checked_ids)
        ids = []
        for idx in self.table.selectionModel().selectedRows():
            item = self.table.item(idx.row(), 1)
            if item:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def _on_item_changed(self, item):
        if self._refreshing or item.column() != 0:
            return
        did = item.data(Qt.ItemDataRole.UserRole)
        if did is None:
            return
        if item.checkState() == Qt.CheckState.Checked:
            self._checked_ids.add(did)
        else:
            self._checked_ids.discard(did)

    def _on_header_clicked(self, section):
        if section != 0 or not self._visible_ids:
            return
        if all(d in self._checked_ids for d in self._visible_ids):
            for d in self._visible_ids:
                self._checked_ids.discard(d)
            self.table.horizontalHeaderItem(0).setText("☐")
        else:
            self._checked_ids.update(self._visible_ids)
            self.table.horizontalHeaderItem(0).setText("☑")
        self.refresh()

    def on_select(self):
        ids = self.selected_ids()
        if not ids:
            return
        r = self.store.get(ids[0])
        if not r:
            return
        job = self.manager.job_for(r["id"])
        pct = (r["downloaded"] / r["total"] * 100) if r["total"] > 0 else 0
        self.detail.setPlainText(
            f"{tr('d_name')}: {r['filename']}\n{tr('d_url')}: {r['url']}\n{tr('d_folder')}: {r['save_dir']}\n"
            f"{tr('d_size')}: {fmt_bytes(r['total'])} · {tr('d_done')}: {fmt_bytes(r['downloaded'])} ({pct:.1f}%)\n"
            f"{tr('d_status')}: {status_text(r['status'])} · {tr('d_kind')}: {r['kind']} · {tr('d_cat')}: {r['category']}\n"
            f"{tr('d_segplan')}: {r['segments']} · {tr('d_limit')}: {fmt_speed(r['speed_limit']) if r['speed_limit'] else tr('d_nolimit')}\n"
            + (f"Error: {r['error']}\n" if r["error"] else "")
            + (f"{tr('d_sched')}: {time.strftime('%d-%m-%Y %H:%M', time.localtime(r['schedule_at']))}\n" if r["schedule_at"] else ""))
        fr = self.seg_fractions.get(r["id"])
        if fr is None and r["total"] > 0 and job and getattr(job, "segments_state", None):
            n = len(job.segments_state)
            seg_size = r["total"] / n if n else r["total"]
            fr = [min(1.0, (job.segments_state[i] / seg_size if seg_size else 0)) for i in range(n)]
        self.seg_widget.set_data(fr or [])
        self.graph.set_samples(self.speed_hist.get(r["id"], []))
        logs = self.logs_by_id.get(r["id"], [])
        if job and getattr(job, "logs", None):
            logs = list(job.logs)
        self.log_view.setPlainText("\n".join(logs[-200:]))

    # ---------- aksi ----------
    def _confirm_download(self, whats, save_dir):
        """Popup lanjut/tidak sebelum unduhan baru dimulai (bisa dimatikan di Pengaturan)."""
        if not self.settings.get("confirm_download"):
            return True
        whats = [w for w in whats if w]
        if not whats:
            return True
        if len(whats) == 1:
            text = tr("confirm_one").format(what=whats[0][:300], dir=save_dir or "-")
        else:
            text = tr("confirm_many").format(n=len(whats), what=whats[0][:300], dir=save_dir or "-")
        box = QMessageBox(self)
        box.setWindowTitle(tr("confirm_title"))
        box.setText(text)
        by = box.addButton(tr("yes"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("no"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is by

    def on_add(self):
        dlg = AddDialog(self, self.settings)
        if dlg.exec():
            v = dlg.values()
            if v["url"] and self._confirm_download([v.get("filename") or v["url"]], v.get("save_dir")):
                self.manager.add(**v)
                self.refresh()

    def on_batch(self):
        dlg = BatchDialog(self, self.settings)
        if dlg.exec():
            urls, folder = dlg.urls()
            if urls and not self._confirm_download(urls, folder):
                return
            for u in urls:
                self.manager.add(u, save_dir=folder, start_now=False)
            for r in self.store.all():
                if r["status"] == "queued":
                    self.manager.start(r["id"])
            self.refresh()

    def on_resume_sel(self):
        for did in self.selected_ids():
            self.manager.start(did)
        self.refresh()

    def on_pause_sel(self):
        for did in self.selected_ids():
            self.manager.pause(did)
        self.refresh()

    def on_delete_sel(self, delete_file=False):
        for did in self.selected_ids():
            self.manager.delete(did, delete_file=delete_file)
            self._checked_ids.discard(did)
        self.refresh()

    def on_settings(self):
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec():
            CUR_LANG["code"] = self.settings.get("language") or "id"
            self.retranslate()
            self.manager.apply_global_limit()
            self._update_mode_chip()
            apply_theme(QApplication.instance(), self.settings)
            self._apply_3d_effects()
            self.refresh()

    def open_file(self):
        ids = self.selected_ids()
        if not ids:
            return
        r = self.store.get(ids[0])
        path = os.path.join(r["save_dir"], r["filename"])
        if os.path.exists(path):
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa: S606
            else:
                subprocess.Popen(["xdg-open", path])

    def open_folder(self):
        ids = self.selected_ids()
        if not ids:
            return
        r = self.store.get(ids[0])
        if os.path.isdir(r["save_dir"]):
            if sys.platform.startswith("win"):
                os.startfile(r["save_dir"])  # noqa: S606
            else:
                subprocess.Popen(["xdg-open", r["save_dir"]])

    def on_context_menu(self, pos):
        ids = self.selected_ids()
        if not ids:
            return
        menu = QMenu(self)
        statuses = set()
        for d in ids:
            rr = self.store.get(d)
            if rr:
                statuses.add(rr["status"])
        a_resume = menu.addAction(tr("m_resume"), self.on_resume_sel)
        a_resume.setEnabled(bool(statuses & {"paused", "queued", "error", "scheduled"}))
        a_pause = menu.addAction(tr("m_pause"), self.on_pause_sel)
        a_pause.setEnabled(bool(statuses & {"downloading", "merging", "queued", "scheduled"}))
        menu.addAction(tr("m_open_file"), self.open_file)
        menu.addAction(tr("m_open_folder"), self.open_folder)
        r = self.store.get(ids[0])
        if r and r["status"] == "completed" and r["filename"].lower().rsplit(".", 1)[-1] in ("mp4", "mkv", "webm", "mp3", "wav", "flac"):
            menu.addAction(tr("m_convert_mp3"), lambda: self.convert_sel("mp3"))
            menu.addAction(tr("m_convert_mp4"), lambda: self.convert_sel("mp4"))
        a_sched = menu.addAction(tr("m_schedule"), lambda: self.schedule_sel(3600))
        a_sched.setEnabled(bool(statuses - {"completed"}))
        menu.addAction(tr("m_copy"), lambda: QGuiApplication.clipboard().setText(r["url"] if r else ""))
        menu.addSeparator()
        menu.addAction(tr("m_del"), lambda: self.on_delete_sel(False))
        menu.addAction(tr("m_del_file"), lambda: self.on_delete_sel(True))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def schedule_sel(self, delay_seconds):
        for did in self.selected_ids():
            self.manager.pause(did)
            self.store.update(did, status="scheduled", schedule_at=time.time() + delay_seconds)
        self.refresh()

    def convert_sel(self, kind):
        ids = self.selected_ids()
        if not ids:
            return
        from ydm.converter import convert, target_for
        import threading
        r = self.store.get(ids[0])
        src = os.path.join(r["save_dir"], r["filename"])
        dst = target_for(src, kind)
        def run():
            try:
                convert(src, dst)
                self._status(tr("conv_done").format(p=dst))
            except Exception as e:
                self._status(tr("conv_fail").format(e=e))
        threading.Thread(target=run, daemon=True).start()
        self._status(tr("conv_running").format(k=kind))

    # ---------- event & timer ----------
    def tick(self):
        self._anim_phase = (self._anim_phase + 1) % 24
        # tiriskan antrean event manager (notifikasi selesai, dll)
        import queue as _q
        while True:
            try:
                kind, did, *args = self.manager.events.get_nowait()
            except _q.Empty:
                break
            if kind == "status" and args and args[0] == "completed":
                r = self.store.get(did)
                if r and self.settings.get("notify_done"):
                    self.tray.showMessage(tr("tray_done"), r["filename"],
                        QSystemTrayIcon.MessageIcon.Information, 4000)
            if kind == "log" and args:
                self.logs_by_id.setdefault(did, []).append(args[0])
            if kind == "progress" and len(args) >= 3:
                downloaded, speed, seg_state = args[0], args[1], args[2]
                self.speed_hist.setdefault(did, []).append(speed)
                r = self.store.get(did)
                if r and r["total"] > 0 and seg_state:
                    n = len(seg_state)
                    seg_size = r["total"] / n
                    self.seg_fractions[did] = [min(1.0, s / seg_size if seg_size else 0) for s in seg_state]
        self.manager.poll()
        self._poll_inbox()
        if self._ytdlp_msg:
            self.tray.showMessage("YDM - yt-dlp", self._ytdlp_msg,
                                  QSystemTrayIcon.MessageIcon.Information, 4000)
            self._status(self._ytdlp_msg)
            self._ytdlp_msg = None
        self.refresh()
        ids = self.selected_ids()
        if ids:
            self.on_select()

    def _inbox_paths(self):
        paths = [os.path.join(DATA_DIR, "inbox.jsonl")]
        la = os.environ.get("LOCALAPPDATA")
        if la:
            paths.append(os.path.join(la, "YDM", "inbox.jsonl"))
        return paths

    def _poll_inbox(self):
        # consume-once: berkas inbox dipindah & dihapus setelah dibaca,
        # jadi riwayat lama tidak pernah diputar ulang pada buka berikutnya
        # (bug duplikat unduhan saat membuka instalasi .exe baru).
        from ydm.inbox import consume_inbox
        from ydm.youtube import is_youtube_url
        for path in self._inbox_paths():
            for data in consume_inbox(path):
                try:
                    url = (data.get("url") or "").strip()
                    if not url:
                        continue
                    label = data.get("filename") or url
                    if not self._confirm_download([label], self.settings.get("download_dir")):
                        continue
                    if data.get("kind") == "youtube" or is_youtube_url(url):
                        self.manager.add(url, headers=data.get("headers") or {},
                                         youtube_quality=data.get("quality") or None,
                                         source="browser")
                    else:
                        self.manager.add(url, filename=data.get("filename") or None,
                                         headers=data.get("headers") or {}, source="browser")
                except Exception:
                    continue

    def on_clipboard(self):
        if not self.settings.get("clipboard_watch"):
            return
        text = (QGuiApplication.clipboard().text() or "").strip()
        if not text or text == self._last_clip:
            return
        self._last_clip = text
        if (is_url(text) or is_magnet(text)) and len(text) < 2048:
            dlg = AddDialog(self, self.settings, prefill=text)
            if dlg.exec():
                v = dlg.values()
                if v["url"]:
                    self.manager.add(**v)
                    self.refresh()

    # ---------- drag & drop ----------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() or e.mimeData().hasText():
            e.acceptProposedAction()
    def dropEvent(self, e):
        items = []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p and p.lower().endswith(".torrent"):
                items.append(p)
            elif u.toString() and is_url(u.toString()):
                items.append(u.toString())
        text = (e.mimeData().text() or "").strip()
        if text and (is_url(text) or is_magnet(text)):
            items.append(text)
        if items and self._confirm_download(items, self.settings.get("download_dir")):
            for it in items:
                self.manager.add(it)
        self.refresh()

    def closeEvent(self, e):
        if self.settings.get("close_to_tray"):
            e.ignore()
            self.hide()
            self.tray.showMessage("YDM", tr("tray_msg"),
                                  QSystemTrayIcon.MessageIcon.Information, 2500)
        else:
            super().closeEvent(e)


# ---------------- tema 3D: putih & ungu gelap, mengikuti mode Windows ----------------
LIGHT_QSS = """
QWidget { background:#fdf6f0; color:#33161c; font-family:"Segoe UI Variable","Segoe UI"; font-size:12px; }
QMainWindow { background:transparent; }
#gundamHeader { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f9e9e2); border-bottom:2px solid #d21f2b; }
#gundamTitle { font-size:17px; font-weight:800; letter-spacing:1px; color:#33161c; background:transparent; }
#gundamSub { font-family:Consolas,monospace; font-size:9px; letter-spacing:3px; color:#a08a84; background:transparent; }
#gundamChip { font-family:Consolas,monospace; font-size:10px; letter-spacing:1px; color:#8f1220; border:1px dashed #c98a80; border-radius:4px; padding:6px 10px; background:#fdf0ea; }
QToolBar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f6e3da); border-bottom:1px solid #e3c2b8; spacing:6px; padding:6px; }
QToolButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f3ddd2); border:1px solid #d9aFA3; border-radius:5px; padding:6px 11px; color:#4a1218; }
QToolButton:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #efc9ba); border-color:#d21f2b; }
QToolButton:pressed { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #eec5b4, stop:1 #f7e3d7); }
QToolButton#btnPrimary { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e02430, stop:1 #8f1220); border:1px solid #5e0a12; color:#ffffff; font-weight:700; }
QToolButton#btnPrimary:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f04438, stop:1 #a31621); }
QToolButton#btnPrimary:pressed { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #8f1220, stop:1 #c8102e); }
QPushButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f3ddd2); border:1px solid #d9afa3; border-radius:11px; padding:5px 12px; color:#4a1218; }
QPushButton:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #efc9ba); border-color:#d21f2b; }
QPushButton:pressed { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #eec5b4, stop:1 #f7e3d7); }
QPushButton:checked { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e02430, stop:1 #8f1220); border-color:#5e0a12; color:#ffffff; font-weight:700; }
QPushButton:disabled { color:#c4a49b; border-color:#ecd9d2; }
QLineEdit, QSpinBox, QComboBox, QDateTimeEdit { background:#ffffff; border:1px solid #d9afa3; border-radius:5px; padding:5px 9px; selection-background-color:#f6c9c0; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border:1px solid #d21f2b; }
QComboBox::drop-down { border:none; width:18px; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #c96a5e; border-radius:4px; background:#ffffff; }
QCheckBox::indicator:checked { background:#d21f2b; border-color:#8f1220; }
QTableWidget { background:#ffffff; alternate-background-color:#fdf1ea; gridline-color:#f0d5ca; border:1px solid #e0b7a9; border-radius:8px; selection-background-color:#f3c1b2; selection-color:#33161c; }
QHeaderView::section { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #571e26, stop:1 #3d0f16); color:#ffffff; font-family:Consolas,monospace; font-weight:700; letter-spacing:1px; border:none; border-right:1px solid #5e2731; padding:6px; }
QProgressBar { border:1px solid #d9a08e; border-radius:4px; background:#f7e3d7; text-align:center; color:#5e0a12; min-height:14px; font-weight:700; }
QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8f1220, stop:.55 #d21f2b, stop:1 #e8b13c); border-radius:3px; }
QTabWidget::pane { border:1px solid #e0b7a9; border-radius:8px; background:#ffffff; top:-1px; }
QTabBar::tab { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f3ddd2); border:1px solid #e0b7a9; border-bottom:none; border-top-left-radius:6px; border-top-right-radius:6px; padding:6px 16px; margin-right:3px; color:#4a1218; font-weight:600; }
QTabBar::tab:selected { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e02430, stop:1 #8f1220); color:#ffffff; font-weight:700; }
QTextEdit, QPlainTextEdit { background:#ffffff; border:1px solid #e0b7a9; border-radius:6px; }
QStatusBar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #571e26, stop:1 #3d0f16); color:#ffd9a8; font-family:Consolas,monospace; border-top:1px solid #5e2731; }
QMenu { background:#ffffff; border:1px solid #e0b7a9; padding:4px; }
QMenu::item { padding:5px 22px; border-radius:4px; }
QMenu::item:selected { background:#f9e0d4; color:#5e0a12; }
QSplitter::handle { background:#f0d5ca; }
QScrollBar:vertical { background:#f7e8e2; width:11px; margin:0; }
QScrollBar::handle:vertical { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #d98d76, stop:1 #c2503c); border-radius:5px; min-height:26px; }
QScrollBar:horizontal { background:#f7e8e2; height:11px; margin:0; }
QScrollBar::handle:horizontal { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #d98d76, stop:1 #c2503c); border-radius:5px; min-width:26px; }
QScrollBar::add-line, QScrollBar::sub-line { height:0; width:0; }
QDialogButtonBox QPushButton { min-width:78px; }
QToolTip { background:#3d0f16; color:#ffffff; border:1px solid #8f1220; padding:4px 8px; }

#stage { background:transparent; }
#card { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #fffaf5, stop:1 #f7e8e2); border:1px solid #e0b7a9; border-radius:12px; }
#card[maxi="true"] { border-radius:0; border:none; }
#bodyPad { background:transparent; }
#toolbarRow { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f6e3da); border-bottom:1px solid #e3c2b8; }
#gundamHeader { border-top-left-radius:11px; border-top-right-radius:11px; }
#winBtn { background:rgba(255,255,255,.55); border:1px solid #d9afa3; border-radius:4px; color:#4a1218; font-weight:700; padding:0; }
#winBtn:hover { background:#ffffff; border-color:#d21f2b; }
#winClose { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e02430, stop:1 #a31621); border:1px solid #5e0a12; border-radius:4px; color:#ffffff; font-weight:700; padding:0; }
#winClose:hover { background:#f04438; }
QPushButton#pill { border-radius:13px; padding:5px 13px; min-height:15px; }
#panelBox { background:#ffffff; border:1px solid #e0b7a9; border-radius:8px; }
#tabPage { background:#ffffff; }
#statusBand { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #571e26, stop:1 #3d0f16); border-radius:6px; }
#statusDot { color:#37d67a; background:transparent; font-size:11px; }
#statusText { color:#ffd9a8; font-family:Consolas,monospace; background:transparent; }
#statusRight { color:#e8b13c; font-family:Consolas,monospace; font-weight:700; background:transparent; }
"""

DARK_QSS = """
QWidget { background:#17060a; color:#f6e9e4; font-family:"Segoe UI Variable","Segoe UI"; font-size:12px; }
QMainWindow { background:transparent; }
#gundamHeader { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #38141c, stop:1 #1c0d12); border-bottom:2px solid #d21f2b; }
#gundamTitle { font-size:17px; font-weight:800; letter-spacing:1px; color:#f6e9e4; background:transparent; }
#gundamSub { font-family:Consolas,monospace; font-size:9px; letter-spacing:3px; color:#c09a92; background:transparent; }
#gundamChip { font-family:Consolas,monospace; font-size:10px; letter-spacing:1px; color:#e8b13c; border:1px dashed #8a3a41; border-radius:4px; padding:6px 10px; background:#221016; }
QToolBar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3d0f16, stop:1 #221016); border-bottom:1px solid #5e2731; spacing:6px; padding:6px; }
QToolButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #40222a, stop:1 #241016); border:1px solid #8a3a41; border-radius:5px; padding:6px 11px; color:#f6e9e4; }
QToolButton:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #52262e, stop:1 #2c1219); border-color:#ff5964; }
QToolButton:pressed { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #180a0e, stop:1 #2c1219); }
QToolButton#btnPrimary { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e02430, stop:1 #8f1220); border:1px solid #4d060d; color:#ffffff; font-weight:700; }
QToolButton#btnPrimary:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f04438, stop:1 #a31621); }
QToolButton#btnPrimary:pressed { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #8f1220, stop:1 #c8102e); }
QPushButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #40222a, stop:1 #241016); border:1px solid #8a3a41; border-radius:11px; padding:5px 12px; color:#f6e9e4; }
QPushButton:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #52262e, stop:1 #2c1219); border-color:#ff5964; }
QPushButton:pressed { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #180a0e, stop:1 #2c1219); }
QPushButton:checked { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e02430, stop:1 #8f1220); border-color:#4d060d; color:#ffffff; font-weight:700; }
QPushButton:disabled { color:#7a5a54; border-color:#452228; }
QLineEdit, QSpinBox, QComboBox, QDateTimeEdit { background:#221016; border:1px solid #5e2731; border-radius:5px; padding:5px 9px; color:#f6e9e4; selection-background-color:#8f1220; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border:1px solid #ff5964; }
QComboBox::drop-down { border:none; width:18px; }
QComboBox QAbstractItemView { background:#221016; color:#f6e9e4; selection-background-color:#8f1220; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #c2503c; border-radius:4px; background:#221016; }
QCheckBox::indicator:checked { background:#d21f2b; border-color:#ff5964; }
QTableWidget { background:#221016; alternate-background-color:#281219; gridline-color:#452228; border:1px solid #5e2731; border-radius:8px; selection-background-color:#5e1a24; selection-color:#ffffff; color:#f6e9e4; }
QHeaderView::section { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #4a1219, stop:1 #2c0d13); color:#ffd9a8; font-family:Consolas,monospace; font-weight:700; letter-spacing:1px; border:none; border-right:1px solid #5e2731; padding:6px; }
QProgressBar { border:1px solid #8a3a41; border-radius:4px; background:#180a0e; text-align:center; color:#ffe9d6; min-height:14px; font-weight:700; }
QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8f1220, stop:.55 #d21f2b, stop:1 #e8b13c); border-radius:3px; }
QTabWidget::pane { border:1px solid #5e2731; border-radius:8px; background:#221016; top:-1px; }
QTabBar::tab { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #40222a, stop:1 #241016); border:1px solid #5e2731; border-bottom:none; border-top-left-radius:6px; border-top-right-radius:6px; padding:6px 16px; margin-right:3px; color:#f6e9e4; font-weight:600; }
QTabBar::tab:selected { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e02430, stop:1 #8f1220); color:#ffffff; font-weight:700; }
QTextEdit, QPlainTextEdit { background:#1c0d12; border:1px solid #5e2731; border-radius:6px; color:#f6e9e4; }
QStatusBar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3d0f16, stop:1 #17060a); color:#e8b13c; font-family:Consolas,monospace; border-top:1px solid #5e2731; }
QMenu { background:#221016; border:1px solid #5e2731; padding:4px; color:#f6e9e4; }
QMenu::item { padding:5px 22px; border-radius:4px; }
QMenu::item:selected { background:#8f1220; color:#ffffff; }
QSplitter::handle { background:#38141c; }
QScrollBar:vertical { background:#1c0d12; width:11px; margin:0; }
QScrollBar::handle:vertical { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8a3a41, stop:1 #d21f2b); border-radius:5px; min-height:26px; }
QScrollBar:horizontal { background:#1c0d12; height:11px; margin:0; }
QScrollBar::handle:horizontal { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #8a3a41, stop:1 #d21f2b); border-radius:5px; min-width:26px; }
QScrollBar::add-line, QScrollBar::sub-line { height:0; width:0; }
QDialogButtonBox QPushButton { min-width:78px; }
QToolTip { background:#f6e9e4; color:#4a1218; border:1px solid #c2503c; padding:4px 8px; }

#stage { background:transparent; }
#card { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2a0e12, stop:1 #12040a); border:1px solid #5e2731; border-radius:12px; }
#card[maxi="true"] { border-radius:0; border:none; }
#bodyPad { background:transparent; }
#toolbarRow { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3d0f16, stop:1 #221016); border-bottom:1px solid #5e2731; }
#gundamHeader { border-top-left-radius:11px; border-top-right-radius:11px; }
#winBtn { background:rgba(0,0,0,.25); border:1px solid #8a3a41; border-radius:4px; color:#f6e9e4; font-weight:700; padding:0; }
#winBtn:hover { background:#52262e; border-color:#ff5964; }
#winClose { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e02430, stop:1 #8f1220); border:1px solid #4d060d; border-radius:4px; color:#ffffff; font-weight:700; padding:0; }
#winClose:hover { background:#f04438; }
QPushButton#pill { border-radius:13px; padding:5px 13px; min-height:15px; }
#panelBox { background:#221016; border:1px solid #5e2731; border-radius:8px; }
#tabPage { background:#221016; }
#statusBand { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3d0f16, stop:1 #17060a); border-radius:6px; }
#statusDot { color:#37d67a; background:transparent; font-size:11px; }
#statusText { color:#e8b13c; font-family:Consolas,monospace; background:transparent; }
#statusRight { color:#e8b13c; font-family:Consolas,monospace; font-weight:700; background:transparent; }
"""

def _system_dark():
    """Mode gelap Windows: Qt colorScheme dulu, cadangan registri."""
    try:
        app = QApplication.instance()
        if app is not None:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Dark:
                return True
            if scheme == Qt.ColorScheme.Light:
                return False
    except Exception:
        pass
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(val) == 0
    except Exception:
        return False

def resolve_dark(settings):
    theme = settings.get("theme")
    if theme == "Gelap":
        return True
    if theme == "Terang":
        return False
    return _system_dark()

def apply_theme(app, settings):
    dark = resolve_dark(settings)
    DARK_MODE["on"] = dark
    if dark:
        PAL.update({
            "seg_empty_top": "#3a1a21", "seg_empty_bot": "#241016", "seg_empty_pen": "#8a3a41",
            "graph_bg": "#1c0d12", "graph_line": "#ff5964", "graph_glow": (255, 89, 100, 70),
            "graph_text": "#e8b13c"})
    else:
        PAL.update({
            "seg_empty_top": "#f9e9e2", "seg_empty_bot": "#f0d5ca", "seg_empty_pen": "#d9a08e",
            "graph_bg": "#fdf1ea", "graph_line": "#d21f2b", "graph_glow": (210, 31, 43, 60),
            "graph_text": "#8f1220"})
    app.setStyleSheet(DARK_QSS if dark else LIGHT_QSS)


def _ytdlp_bootstrap():
    """Mode tersembunyi untuk build .exe: YDM.exe --ytdlp <argumen yt-dlp...>
    menjalankan CLI yt-dlp yang terbundel, lalu keluar."""
    idx = sys.argv.index("--ytdlp")
    sys.argv = ["yt-dlp"] + sys.argv[idx + 1:]
    from yt_dlp import main as _yt_main
    try:
        _yt_main()
    except SystemExit as e:
        raise
    return 0


def main():
    if "--ytdlp" in sys.argv:
        return _ytdlp_bootstrap()
    if "--ytdlp-update" in sys.argv:
        from ydm.updater import check_and_maybe_update
        res = check_and_maybe_update(DATA_DIR, auto_update=True, force=True)
        print(res)
        return 0 if not res.get("error") else 1
    smoke = "--smoke" in sys.argv
    if smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    settings = Settings(SETTINGS_PATH)
    CUR_LANG["code"] = settings.get("language") or "id"
    store = Store(DB_PATH)
    manager = DownloadManager(store, settings)
    app = QApplication(sys.argv)
    app.setApplicationName("Yukii Download Manager")
    app.setWindowIcon(make_app_icon())
    app.aboutToQuit.connect(manager.shutdown)
    apply_theme(app, settings)
    win = MainWindow(settings, store, manager)
    try:
        def _on_scheme_changed(*_a):
            # mode "Sistem": ikuti perubahan mode Windows secara langsung
            if settings.get("theme") == "Sistem":
                apply_theme(app, settings)
                win._apply_3d_effects()
                win.refresh()
        app.styleHints().colorSchemeChanged.connect(_on_scheme_changed)
    except Exception:
        pass
    win.show()
    if smoke:
        QTimer.singleShot(1500, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
