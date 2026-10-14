"""Daftarkan YDM Native Messaging Host untuk Chrome, Edge, Brave, Chromium, Firefox.

Menulis manifest ke %LOCALAPPDATA%\\YDM\\NativeHost\\ dan kunci registri HKCU
(tanpa admin). ID ekstensi bawaan di bawah HARUS sama dengan ID yang diberikan
browser saat ekstensi dimuat; untuk pemakaian unpacked, Chrome/Edge memberi ID
berdasarkan path folder - karena itu installer ini mendukung mode 'dev':
ia mendaftarkan allowed_origins untuk ID yang kamu berikan lewat argumen.

Contoh:
  python install_native_host.py --extension-id abcd...wxyz
Tanpa argumen, manifest memakai placeholder dan mencetak petunjuk.
"""
import argparse, json, os, sys

HOST_NAME = "id.yukii.ydm"

def manifest_dir():
    la = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(la, "YDM", "NativeHost")
    os.makedirs(d, exist_ok=True)
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extension-id", action="append", default=[],
                    help="ID ekstensi Chromium (boleh diulang). Tanpa ini, placeholder dipakai.")
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    bat = os.path.join(here, "ydm_native_host.bat")
    ids = args.extension_id or ["EXTENSION_ID_DARI_BROWSER"]
    origins = [f"chrome-extension://{i}/" for i in ids]

    chromium_manifest = {
        "name": HOST_NAME,
        "description": "Yukii Download Manager",
        "path": bat,
        "type": "stdio",
        "allowed_origins": origins,
    }
    firefox_manifest = {
        "name": HOST_NAME,
        "description": "Yukii Download Manager",
        "path": bat,
        "type": "stdio",
        "allowed_extensions": ["ydm@yukii.id"],
    }
    d = manifest_dir()
    chromium_path = os.path.join(d, HOST_NAME + ".chromium.json")
    firefox_path = os.path.join(d, HOST_NAME + ".firefox.json")
    with open(chromium_path, "w", encoding="utf-8") as f:
        json.dump(chromium_manifest, f, indent=2)
    with open(firefox_path, "w", encoding="utf-8") as f:
        json.dump(firefox_manifest, f, indent=2)

    if sys.platform.startswith("win"):
        import winreg
        targets_chromium = [
            r"Software\Google\Chrome\NativeMessagingHosts",
            r"Software\Microsoft\Edge\NativeMessagingHosts",
            r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
            r"Software\Chromium\NativeMessagingHosts",
        ]
        for base in targets_chromium:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + HOST_NAME)
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, chromium_path)
            winreg.CloseKey(key)
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Mozilla\NativeMessagingHosts" + "\\" + HOST_NAME)
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, firefox_path)
        winreg.CloseKey(key)
        print("Terdaftar untuk Chrome, Edge, Brave, Chromium, Firefox (HKCU).")
    print(f"Manifest Chromium: {chromium_path}")
    print(f"Manifest Firefox : {firefox_path}")
    if ids == ["EXTENSION_ID_DARI_BROWSER"]:
        print("\nPERHATIAN: belum ada ID ekstensi asli.")
        print("1) Muat folder extension/chromium di chrome://extensions (mode pengembang).")
        print("2) Catat ID yang muncul, lalu jalankan lagi:")
        print("   python install_native_host.py --extension-id <ID>")

if __name__ == "__main__":
    main()
