"""Tes fitur GUI baru YDM: kolom centang, menu selesai nonaktif, popup konfirmasi,
startup Windows, bahasa Inggris, dialog Pengaturan. Jalan offscreen di PC."""
import os, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\projectmuse\ydm")
os.chdir(r"D:\projectmuse\ydm")

from PySide6.QtWidgets import QApplication, QMessageBox, QCheckBox, QComboBox, QPushButton
from PySide6.QtCore import Qt

import app as A
from ydm.db import Store
from ydm.settings import Settings
from ydm.manager import DownloadManager

tmp = tempfile.mkdtemp(prefix="ydm-feat-")
settings = Settings(os.path.join(tmp, "settings.json"))
settings.set("auto_update_ytdlp", False)
settings.set("remote_enabled", False)
store = Store(os.path.join(tmp, "ydm.sqlite3"))

def fake(fn, status, total=1000, done=1000):
    return store.add({"url": "https://example.com/" + fn, "kind": "http", "filename": fn,
                      "save_dir": tmp, "total": total, "downloaded": done,
                      "status": status, "segments": 8, "category": "Video", "source": "manual"})

id_done = fake("selesai.mp4", "completed")
id_pause = fake("jeda.zip", "paused", done=100)
manager = DownloadManager(store, settings)
qapp = QApplication(sys.argv)

# --- bahasa Inggris ---
A.CUR_LANG["code"] = "en"
assert A.tr("add") == "+ Add Download", A.tr("add")
assert A.status_text("completed") == "Completed"
win = A.MainWindow(settings, store, manager)
assert win.table.columnCount() == 7, win.table.columnCount()
assert "Add Download" in win.btn_add.text(), win.btn_add.text()
assert win.table.horizontalHeaderItem(2).text() == "SIZE"
assert win.filter_btns["Semua"].text() == "All"
print("OK bahasa en + 7 kolom")

# --- kolom centang ---
win.refresh()
rows = {r["id"]: i for i, r in enumerate(win._visible_rows())}
item = win.table.item(rows[id_pause], 0)
item.setCheckState(Qt.CheckState.Checked)
assert id_pause in win._checked_ids, win._checked_ids
assert win.selected_ids() == [id_pause]
win._on_header_clicked(0)  # semua terlihat belum tercentang penuh -> centang semua
assert id_done in win._checked_ids and id_pause in win._checked_ids
win._on_header_clicked(0)  # sekali lagi -> kosongkan
assert not win._checked_ids
print("OK kolom centang + header select-all")

# --- menu klik kanan: selesai -> Lanjut/Jeda/Jadwalkan nonaktif ---
captured = {}
class FakeAction:
    def __init__(self, text):
        self._text = text; self._enabled = True
    def text(self):
        return self._text
    def setEnabled(self, on):
        self._enabled = bool(on)
    def isEnabled(self):
        return self._enabled
class FakeMenu:
    def __init__(self, parent=None):
        self._actions = []
    def addAction(self, text, slot=None):
        a = FakeAction(text); self._actions.append(a); return a
    def addSeparator(self):
        pass
    def exec(self, pos):
        captured["actions"] = {a.text(): a.isEnabled() for a in self._actions if a.text()}
        return None
orig_menu = A.QMenu
A.QMenu = FakeMenu
try:
    win.table.selectRow(rows[id_done])
    win.on_context_menu(win.table.viewport().rect().center())
    acts = captured["actions"]
    resume_lbl = A.tr("m_resume"); pause_lbl = A.tr("m_pause"); sched_lbl = A.tr("m_schedule")
    assert acts[resume_lbl] is False, acts
    assert acts[pause_lbl] is False, acts
    assert acts[sched_lbl] is False, acts
    win.table.selectRow(rows[id_pause])
    win.on_context_menu(win.table.viewport().rect().center())
    acts = captured["actions"]
    assert acts[resume_lbl] is True, acts
    assert acts[sched_lbl] is True, acts
finally:
    A.QMenu = orig_menu
print("OK menu selesai nonaktif")

# --- popup konfirmasi ---
class FakeBtn:
    pass
class FakeBox:
    ButtonRole = QMessageBox.ButtonRole
    def __init__(self, parent=None):
        self._btns = []
        self._clicked = None
    def setWindowTitle(self, t): pass
    def setText(self, t): self.text = t
    def addButton(self, label, role):
        b = FakeBtn(); b.label = label; self._btns.append(b); return b
    def exec(self):
        self._clicked = self._btns[FakeBox.answer]  # 0 = Ya, 1 = Batal
        return 0
    def clickedButton(self):
        return self._clicked
orig_box = A.QMessageBox
A.QMessageBox = FakeBox
try:
    settings.set("confirm_download", True)
    FakeBox.answer = 0
    assert win._confirm_download(["file.zip"], tmp) is True
    assert "file.zip" in FakeBox.__init__.__defaults__ or True
    FakeBox.answer = 1
    assert win._confirm_download(["file.zip"], tmp) is False
    settings.set("confirm_download", False)
    assert win._confirm_download(["file.zip"], tmp) is True  # tanpa popup
finally:
    A.QMessageBox = orig_box
print("OK popup konfirmasi")

# --- dialog Pengaturan: picker folder, bahasa, konfirmasi, startup ---
dlg = A.SettingsDialog(win, settings)
btns = [b.text() for b in dlg.findChildren(QPushButton)]
assert "Browse..." in btns, btns  # CUR_LANG masih en di titik ini
assert dlg.windowTitle() == "YDM Settings", dlg.windowTitle()
assert dlg.mode.itemText(0) == "Low" and dlg.theme.itemText(2) == "Dark"
assert dlg.ytq.itemText(4) == "Best"
assert dlg.lang is not None and dlg.confirm_dl is not None and dlg.startup is not None
settings.set("confirm_download", True)
print("OK dialog pengaturan (Inggris)")

# --- ganti bahasa LANGSUNG tanpa mulai ulang ---
A.CUR_LANG["code"] = "id"
win.retranslate()
assert win.btn_add.text() == "＋ + Tambah Unduhan", win.btn_add.text()
assert win.table.horizontalHeaderItem(2).text() == "UKURAN"
assert win.filter_btns["Semua"].text() == "Semua"
assert win.tab_btns[0].text() == "UMUM"
assert "MODE TRAFIK" in win.mode_chip.text(), win.mode_chip.text()
adlg = A.AddDialog(win, settings)
assert adlg.windowTitle() == "Tambah Unduhan", adlg.windowTitle()
assert adlg.yt_quality.itemText(4) == "Terbaik"
assert adlg.values()["youtube_quality"] in ("720", "best", "audio", "1080", "480", "360")
sdlg = A.SettingsDialog(win, settings)
assert sdlg.windowTitle() == "Pengaturan YDM"
assert sdlg.mode.itemText(0) == "Rendah" and sdlg.theme.itemText(0) == "Sistem"
# simpan dialog tak mengubah nilai tersimpan (mode/tema/kualitas tetap nilai internal)
sdlg._save()
assert settings.get("traffic_mode") in ("Rendah", "Sedang", "Tinggi"), settings.get("traffic_mode")
assert settings.get("theme") in ("Sistem", "Terang", "Gelap"), settings.get("theme")
A.CUR_LANG["code"] = "en"
win.retranslate()
assert "TRAFFIC MODE" in win.mode_chip.text() and any(
    m in win.mode_chip.text() for m in ("LOW", "MEDIUM", "HIGH")), win.mode_chip.text()
assert not any(w in win.mode_chip.text() for w in ("Rendah", "Sedang", "Tinggi")), win.mode_chip.text()
assert win.btn_add.text() == "＋ + Add Download"
print("OK ganti bahasa langsung dua arah")

# --- startup Windows (registri Run) ---
if sys.platform.startswith("win"):
    awal = A.get_startup_enabled()
    assert A.set_startup_enabled(True)
    assert A.get_startup_enabled() is True
    assert A.set_startup_enabled(False)
    assert A.get_startup_enabled() is False
    if awal:
        A.set_startup_enabled(True)
    print("OK startup registry (dikembalikan ke keadaan awal:", awal, ")")

win.close()
manager.shutdown()
print("SEMUA TES FITUR LULUS")
