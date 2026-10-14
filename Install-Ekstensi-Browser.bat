@echo off
cd /d "%~dp0"
echo Mendaftarkan Native Host YDM untuk Chrome/Edge/Brave/Firefox...
echo.
echo LANGKAH SEBELUMNYA (sekali saja):
echo  1. Buka chrome://extensions atau edge://extensions
echo  2. Aktifkan Mode Pengembang, klik "Muat yang belum dikemas"
echo  3. Pilih folder: %~dp0extension\chromium
echo  4. Catat ID ekstensi yang muncul (32 huruf)
echo.
set /p EID=Masukkan ID ekstensi (kosongkan bila belum ada):
if "%EID%"=="" (
  python native_host\install_native_host.py
) else (
  python native_host\install_native_host.py --extension-id %EID%
)
pause
