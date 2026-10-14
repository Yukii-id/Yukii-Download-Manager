"""YDM Native Messaging Host.

Browser (ekstensi) <-> host ini berbicara lewat stdio: pesan dibingkai
4-byte little-endian length + JSON (standar Chrome/Firefox Native Messaging).
Host meneruskan permintaan unduhan ke %LOCALAPPDATA%\\YDM\\inbox.jsonl,
yang dipantau aplikasi YDM (lihat _poll_inbox di app.py).
Host TIDAK mengunduh apa pun sendiri dan tidak membuka port jaringan.
"""
import json, os, struct, sys

def inbox_path():
    la = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(la, "YDM")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "inbox.jsonl")

def read_msg(stream):
    raw = stream.read(4)
    if not raw or len(raw) < 4:
        return None
    (length,) = struct.unpack("<I", raw)
    if length == 0 or length > 1024 * 1024:
        return None
    data = stream.read(length)
    return json.loads(data.decode("utf-8"))

def write_msg(stream, obj):
    data = json.dumps(obj).encode("utf-8")
    stream.write(struct.pack("<I", len(data)))
    stream.write(data)
    stream.flush()

def main():
    inp = sys.stdin.buffer
    out = sys.stdout.buffer
    while True:
        try:
            msg = read_msg(inp)
        except Exception:
            break
        if msg is None:
            break
        url = (msg.get("url") or "").strip()
        if not url:
            write_msg(out, {"ok": False, "error": "url kosong"})
            continue
        record = {
            "url": url,
            "filename": msg.get("filename") or None,
            "headers": msg.get("headers") or {},
            "source": "browser",
        }
        if msg.get("kind"):
            record["kind"] = msg["kind"]
        if msg.get("quality"):
            record["quality"] = msg["quality"]
        with open(inbox_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        write_msg(out, {"ok": True, "queued": url})

if __name__ == "__main__":
    main()
