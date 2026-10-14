# Yukii Download Manager (YDM) — Panduan

Aplikasi download manager untuk Windows, terinspirasi alur kerja Free Download
Manager: unduhan multi-segmen, pause/resume, torrent, scheduler, integrasi
browser, dan konversi media. Dibangun bertahap dalam satu paket ini.

## Menjalankan

### Cara A — versi .exe portable (untuk PC lain, tanpa Python)
Paket `YDM-Portable.zip` (di folder proyek) berisi folder `YDM` dengan
`YDM.exe`. Salin folder itu ke PC tujuan (mis. ke Desktop/Dokumen), lalu
klik dua kali `YDM.exe`. Tidak perlu Python/PySide6 sama sekali; data
tersimpan di subfolder `data` di samping .exe sehingga foldernya bisa
dipindah utuh. ffmpeg ikut terbundel di `tools\`.
- Ekstensi browser di PC tujuan: muat folder `extension\chromium` seperti
  biasa, lalu jalankan `Install-Ekstensi-Browser-Exe.bat` dan masukkan ID
  ekstensinya (ini mendaftarkan `YDMNativeHost.exe`, bukan Python).
- Update yt-dlp pada versi .exe: otomatis dari dalam aplikasi (mengunduh
  `yt-dlp.exe` resmi ke `data\bin\` bila ada versi lebih baru di PyPI),
  atau jalankan `YDM.exe --ytdlp-update` dari Task Scheduler/terminal.

### Cara B — versi sumber (PC pengembang ini)
1. Klik dua kali `Jalankan-YDM.bat`.
   - Pertama kali, PySide6 dipasang otomatis (butuh internet sekali).
   - Selanjutnya langsung membuka aplikasi.
2. Tombol tutup (X) menyembunyikan aplikasi ke tray (bisa diubah di
   Pengaturan). Keluar sepenuhnya dari menu klik kanan ikon tray.

### Catatan progres unduhan
Progress bar menggerakkan persentase secara bertahap. Untuk YouTube,
total ukuran adalah estimasi gabungan stream video+audio dari yt-dlp
(angka akhir bisa berbeda sedikit setelah penggabungan). Bila total
benar-benar belum diketahui, bar menampilkan animasi "mengunduh..."
bukan 0% diam.

## Fitur per tahap

### Tahap 1 — Inti
- Unduhan HTTP/HTTPS/FTP multi-segmen (bawaan 8, bisa 1–32) dengan deteksi
  dukungan Range; server tanpa Range otomatis memakai aliran tunggal.
- Pause/Resume yang persisten: progres disimpan sebagai berkas `.seg*` dan di
  SQLite (`data/ydm.sqlite3`), aman dilanjutkan setelah aplikasi ditutup.
- Antrian dengan batas unduhan bersamaan, prioritas tampilan, batas kecepatan
  global (Mode Trafik Rendah 256 KB/dtk, Sedang 2 MB/dtk, Tinggi tanpa batas)
  dan batas per-unduhan.
- UI sesuai desain yang disetujui: toolbar, filter (Semua/Mengunduh/Mengantri/
  Dijeda/Selesai/Error/Torrent), cari, panel bawah 4 tab (Umum, Segmen dengan
  peta blok segmen, Kecepatan dengan grafik, Log), status bar.
- Smart file management: file otomatis masuk subfolder per kategori
  (Program/Arsip/Video/Musik/Dokumen/Gambar) — matikan di Pengaturan bila
  tidak diinginkan.
- Drag & drop URL / file `.torrent`, pantau clipboard (dialog konfirmasi),
  mode ringkas, tema Sistem/Terang/Gelap, notifikasi tray saat selesai.

### Tahap 2 — Torrent, Scheduler, Browser
- **Torrent/magnet** memakai libtorrent (opsional):
  `pip install -r requirements-optional.txt`
  Tanpa itu, unduhan HTTP tetap normal dan torrent menampilkan pesan jelas.
  Prioritas berkas torrent & seeding lanjutan belum termasuk (setelah selesai,
  torrent dijeda otomatis).
- **Scheduler**: pada dialog Tambah, centang "Jadwalkan mulai pada" — atau
  klik kanan unduhan > "Jadwalkan 1 jam lagi".
- **Ekstensi browser**: lihat bagian khusus di bawah.

### Tahap 3 — Media, Remote, Batch
- **Konversi ffmpeg**: klik kanan unduhan media yang selesai > Konversi ke
  MP3/MP4. Memakai ffmpeg di PATH (di PC ini tersedia; bila tidak, ffmpeg
  milik FDM dipakai sebagai cadangan).
- **Batch**: tombol Batch — tempel hingga 100 URL, satu per baris.
- **Remote control lokal**: Pengaturan > aktifkan remote. Server hanya
  mengikat 127.0.0.1, wajib token (`data/remote_token.txt`):
  - `GET  /api/downloads` — daftar unduhan
  - `POST /api/downloads` `{"url": "..."}` — tambah unduhan
  Header: `X-YDM-Token: <token>`. Berkas hasil unduhan tidak diekspos.

## Ekstensi browser (Chrome/Edge/Brave/Firefox)

1. Jalankan aplikasi YDM sekali agar folder datanya terbentuk.
2. Di browser: buka `chrome://extensions` (atau `edge://extensions`),
   aktifkan Mode Pengembang > "Muat yang belum dikemas" > pilih folder
   `extension\chromium`. Untuk Firefox: `about:debugging` > "This Firefox" >
   "Load Temporary Add-on" > pilih `extension\firefox\manifest.json`.
3. Catat **ID ekstensi** yang diberikan browser.
4. Klik dua kali `Install-Ekstensi-Browser.bat`, masukkan ID tadi.
   Ini mendaftarkan Native Messaging Host (`id.yukii.ydm`) di HKCU untuk
   Chrome, Edge, Brave, Chromium, dan Firefox — tanpa hak admin.
5. Uji: klik kanan sebuah link file > "Unduh dengan YDM". Unduhan harus
   muncul di aplikasi. Pengalihan unduhan otomatis bisa diatur di popup /
   halaman opsi ekstensi (bawaan: hanya file >= 1 MB).
6. Bila YDM diperbarui (mis. ada fitur ekstensi baru seperti tombol
   YouTube), buka lagi halaman ekstensi dan klik tombol muat ulang
   (reload) pada ekstensi YDM agar versi terbaru dari folder yang sama
   aktif.

Cara kerja: ekstensi meneruskan URL + cookies sesi + referrer ke program
kecil `native_host/ydm_native_host.py` (lewat stdio), yang menulis ke
`%LOCALAPPDATA%\YDM\inbox.jsonl`; aplikasi YDM memantau berkas itu.
Tidak ada port jaringan yang dibuka untuk jalur ini.

## Pengujian

- `python tests/test_engine.py` — menguji unduh multi-segmen (hash SHA-256
  harus sama), pause/resume, dan server tanpa Range memakai server lokal.
- `python app.py --smoke` — membuka jendela secara offscreen lalu menutup;
  memeriksa GUI bisa dibuat tanpa error.

## Struktur folder

```
app.py                  GUI utama (PySide6)
Jalankan.py / .bat      peluncur (pasang dependensi sekali)
ydm/                    engine, database, manager, torrent, remote, converter
native_host/            penghubung ekstensi browser <-> aplikasi
extension/chromium/     ekstensi Chrome/Edge/Brave (MV3)
extension/firefox/      ekstensi Firefox
tests/                  tes otomatis engine
data/                   dibuat saat jalan: ydm.sqlite3, settings.json,
                        remote_token.txt (hanya bila remote aktif)
```

### Tahap 4 — YouTube + update otomatis yt-dlp
- **Tombol di halaman YouTube**: setelah ekstensi dimuat/dimuat ulang, di
  bawah player video muncul tombol "Unduh dengan YDM". Klik tombol itu untuk
  membuka panel kualitas: 1080p / 720p / 480p / 360p / Terbaik / Audio MP3.
  Pilihan dikirim lewat native host ke aplikasi; unduhan tampil di daftar
  seperti unduhan biasa (judul asli video, progres, kecepatan).
- **Tempel link juga bisa**: dialog Tambah Unduhan otomatis mengenali URL
  youtube.com / youtu.be / Shorts / Music dan memakai kolom "Kualitas
  YouTube" pada dialog itu.
- Mesinnya yt-dlp (subproses) + ffmpeg untuk menggabungkan video & audio.
  Pause menghentikan subproses dan fragmen `.part` disimpan, resume
  melanjutkan. Video dibatasi usia/privat: isi Pengaturan >
  "Cookies YouTube dari browser" (chrome/edge/firefox) agar memakai sesi
  login browser. Playlist tidak diunduh (satu video per tautan tonton).
- **Update yt-dlp otomatis** (menjawab perubahan sistem YouTube):
  1. Di dalam aplikasi: saat aplikasi dibuka, maksimal sekali per 24 jam
     YDM mengecek versi terbaru yt-dlp di PyPI; bila lebih baru, langsung
     diperbarui via pip dan berlaku untuk unduhan berikutnya (tanpa mulai
     ulang aplikasi). Matikan lewat Pengaturan > "Update yt-dlp otomatis".
  2. Di luar aplikasi: Task Scheduler Windows **"YDM Update yt-dlp"**
     berjalan tiap Senin 09:00 menjalankan `Update-yt-dlp.bat`
     (log: `data\update-ytdlp.log`), jadi tetap mutakhir walau aplikasi
     jarang dibuka. Cek manual kapan pun: klik dua kali bat itu, atau
     `python -m ydm.updater --check`.
  Status cek terakhir tersimpan di `data\ytdlp_update.json`.
  Catatan: yang diperbarui hanya paket resmi yt-dlp dari PyPI lewat pip.

## Batasan yang diketahui (jujur)

- Clone ini bukan FDM: tidak ada HTML Spider (unduh satu situs penuh),
  upload manager, dan pemeriksaan antivirus. Batch + ekstensi menutup
  sebagian besar kebutuhan itu. Situs video selain YouTube belum didukung
  tombol khusus (tempel URL halamannya tetap bisa dicoba lewat yt-dlp dari
  dialog Tambah hanya untuk YouTube; situs lain memakai unduhan biasa).
- Ekstensi mode unpacked: ID berubah bila folder ekstensi dipindah —
  jalankan lagi `Install-Ekstensi-Browser.bat` setelah memindah.
- Unduhan dari situs dengan link bertanda tangan sangat singkat tetap
  bergantung kecepatan penerusan cookies oleh ekstensi.

## Perbaikan 13 Okt 2026 (malam): unduhan dari ekstensi terputar ulang
Dulu berkas jembatan ekstensi (inbox) tidak pernah dikosongkan, jadi setiap aplikasi dibuka lagi - terutama instalasi .exe baru - unduhan lama dari browser diunduh ulang. Sekarang inbox dikonsumsi sekali (berkas dipindah & dihapus setelah dibaca), jadi riwayat lama tidak akan terputar ulang.

## Tema 3D Putih & Ungu (Okt 2026)
Judul jendela sekarang hanya "Yukii Download Manager". Tema UI baru: nuansa 3D putih & ungu gelap - tombol bergradasi dengan bayangan, tombol Unduhan Baru bercahaya, dan kilau bergerak pada bilah progres unduhan aktif. Pilihan Tema "Sistem" (bawaan) mengikuti mode Windows: Windows mode terang = tema putih-ungu, Windows mode gelap = tema ungu gelap; perubahan mode Windows diikuti langsung tanpa restart. Bisa juga dipaksa lewat Pengaturan > Tema: Terang/Gelap.

## Tema Gundam — Red Comet (Okt 2026)
Tema bawaan aplikasi sekarang "Red Comet": baja marun gelap, aksen merah Char + emas, dengan logo kepala RX-78-2 Gundam asli di pita judul dan sebagai ikon aplikasi/.exe/tray. Bilah progres bergradasi merah ke emas dengan kilau bergerak, peta segmen jadi blok emas menyala, label ala HUD (Consolas). Pengaturan tema diset "Gelap" agar tampil persis desain ini; pilihan "Terang" memberi versi ivory-nya, dan "Sistem" tetap mengikuti mode Windows (terang = versi ivory, gelap = Red Comet penuh). Catatan adaptasi: sudut miring (skew) pada preview HTML tidak bisa 1:1 di Qt, diganti sudut tegas + gradasi & cahaya.

## Penyesuaian persis preview Red Comet (Okt 2026)
Jendela utama kini tanpa bingkai Windows (frameless) berbentuk kartu melayang bersudut bulat + bayangan, persis poster preview: pita judul khusus berisi logo Gundam + tombol minimize/maksimalkan/tutup (tutup merah) yang bisa didrag untuk memindah jendela (klik dua kali = maksimalkan; saat dimaksimalkan kartu memenuhi layar). Tombol toolbar & tab digambar sudut potong (chamfer), bilah progres miring (parallelogram) gradasi merah ke emas dengan kilau bergerak, baris unduhan dua baris (nama + meta), status tampil sebagai chip warna ala HUD, dan ada watermark kepala Gundam samar di sudut tabel. Satu-satunya yang tetap tidak bisa disamakan: kemiringan 3D seluruh jendela pada gambar preview adalah efek presentasi poster - jendela aplikasi sungguhan harus tegak agar bisa dipakai.

## Fitur baru (15 Okt 2026)
- Pengaturan kini punya tombol "Pilih..." di samping kolom Folder unduhan (klik untuk memilih folder).
- Popup konfirmasi "Mulai Unduhan?" muncul sebelum setiap unduhan baru dimulai: dari tombol Tambah, Batch, kiriman ekstensi browser, dan drag & drop. Bisa dimatikan lewat Pengaturan > "Popup konfirmasi sebelum download dimulai".
- Pengaturan > "Jalankan YDM otomatis saat Windows mulai (startup)": menghidupkan/mematikan entri startup Windows untuk pengguna ini.
- Bahasa antarmuka bisa diganti Indonesia / English di Pengaturan dan LANGSUNG berlaku saat itu juga (semua tombol, tabel, menu, dialog, tray ikut berubah, tanpa mulai ulang).
- Kolom centang (select) di daftar unduhan: centang baris untuk memilih banyak sekaligus, klik kotak di header untuk memilih/melepas semua yang tampil; tombol Lanjut/Jeda/Hapus dan menu klik kanan bekerja pada yang dicentang.
- Menu klik kanan pada unduhan yang sudah Selesai: Lanjut, Jeda, dan Jadwalkan otomatis tidak bisa diklik (abu-abu).
