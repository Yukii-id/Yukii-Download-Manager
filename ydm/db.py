import json, os, sqlite3, threading, time

SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 url TEXT NOT NULL DEFAULT '',
 kind TEXT NOT NULL DEFAULT 'http',
 filename TEXT NOT NULL DEFAULT 'download',
 save_dir TEXT NOT NULL DEFAULT '',
 total INTEGER NOT NULL DEFAULT -1,
 downloaded INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'queued',
 segments INTEGER NOT NULL DEFAULT 8,
 speed_limit INTEGER NOT NULL DEFAULT 0,
 priority INTEGER NOT NULL DEFAULT 0,
 category TEXT NOT NULL DEFAULT 'Lainnya',
 tags TEXT NOT NULL DEFAULT '',
 headers TEXT NOT NULL DEFAULT '{}',
 schedule_at REAL NOT NULL DEFAULT 0,
 error TEXT NOT NULL DEFAULT '',
 created_at REAL NOT NULL DEFAULT 0,
 finished_at REAL NOT NULL DEFAULT 0,
 source TEXT NOT NULL DEFAULT ''
);
"""

class Store:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def add(self, d):
        cols = ["url","kind","filename","save_dir","total","downloaded","status","segments",
                "speed_limit","priority","category","tags","headers","schedule_at","error",
                "created_at","finished_at","source"]
        vals = [d.get(c, "" if isinstance(c, str) else 0) for c in cols]
        vals[cols.index("headers")] = json.dumps(d.get("headers", {}))
        vals[cols.index("created_at")] = d.get("created_at", time.time())
        with self._lock:
            cur = self._conn.execute(
                f"INSERT INTO downloads({','.join(cols)}) VALUES({','.join('?'*len(cols))})", vals)
            self._conn.commit()
            return cur.lastrowid

    def get(self, did):
        with self._lock:
            r = self._conn.execute("SELECT * FROM downloads WHERE id=?", (did,)).fetchone()
        return self._row(r) if r else None

    def all(self):
        with self._lock:
            rows = self._conn.execute("SELECT * FROM downloads ORDER BY priority DESC, id DESC").fetchall()
        return [self._row(r) for r in rows]

    def update(self, did, **kw):
        if "headers" in kw:
            kw["headers"] = json.dumps(kw["headers"])
        if not kw:
            return
        sets = ",".join(f"{k}=?" for k in kw)
        with self._lock:
            self._conn.execute(f"UPDATE downloads SET {sets} WHERE id=?", (*kw.values(), did))
            self._conn.commit()

    def delete(self, did):
        with self._lock:
            self._conn.execute("DELETE FROM downloads WHERE id=?", (did,))
            self._conn.commit()

    def close(self):
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass

    @staticmethod
    def _row(r):
        d = dict(r)
        try:
            d["headers"] = json.loads(d.get("headers") or "{}")
        except Exception:
            d["headers"] = {}
        return d
