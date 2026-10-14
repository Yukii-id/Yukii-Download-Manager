"""Konsumsi inbox ekstensi browser dengan semantik *consume-once*.

Bug lama: aplikasi membaca inbox.jsonl dari offset 0 setiap proses mulai
(offset hanya disimpan di memori) dan berkasnya tidak pernah dikosongkan,
sehingga SETIAP aplikasi dibuka - apalagi instalasi .exe baru yang
databasenya kosong - seluruh riwayat inbox diputar ulang dan unduhan lama
diunduh lagi.

Perbaikan: konsumsi dilakukan dengan memindahkan (rename) berkas inbox
secara atomik ke berkas kerja milik proses ini, membacanya, lalu
menghapusnya. Penulis (native host) selalu membuka path inbox per pesan,
jadi setelah rename ia akan membuat inbox.jsonl baru untuk pesan
berikutnya. Bila rename gagal (berkas sedang dibuka penulis), siklus ini
dilewati dan dicoba lagi pada poll berikutnya.
"""
import json, os

def consume_inbox(path, pid=None):
    """Ambil semua record dari inbox di `path`. Mengembalikan list[dict].

    Berkas inbox di `path` tidak ada lagi setelah fungsi ini berhasil
    (sudah dipindah & dihapus); pesan baru akan membuat berkas baru.
    """
    if not os.path.exists(path):
        return []
    work = f"{path}.processing-{pid if pid is not None else os.getpid()}"
    try:
        os.replace(path, work)
    except OSError:
        return []  # sedang ditulis native host; coba lagi nanti
    records = []
    try:
        with open(work, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                if isinstance(data, dict) and (data.get("url") or "").strip():
                    records.append(data)
    except OSError:
        return []
    finally:
        try:
            os.remove(work)
        except OSError:
            pass
    return records
