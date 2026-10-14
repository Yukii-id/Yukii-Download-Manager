# Daftarkan YDMNativeHost.exe untuk Chrome/Edge/Brave/Chromium/Firefox.
# Untuk paket .exe portable (tanpa Python). Jalankan dari folder paket:
#   powershell -ExecutionPolicy Bypass -File Install-NativeHost-Exe.ps1 -ExtensionId <ID ekstensi>
param(
    [Parameter(Mandatory = $false)]
    [string]$ExtensionId = ""
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
# skrip ini ada di native_host\ di paket sumber, atau di akar paket portable
$hostExe = Join-Path $here "YDMNativeHost.exe"
if (-not (Test-Path $hostExe)) { $hostExe = Join-Path (Split-Path $here -Parent) "YDMNativeHost.exe" }
if (-not (Test-Path $hostExe)) { throw "YDMNativeHost.exe tidak ditemukan di samping paket." }

$name = "id.yukii.ydm"
$dir = Join-Path $env:LOCALAPPDATA "YDM\NativeHost"
New-Item -ItemType Directory -Force $dir | Out-Null

if (-not $ExtensionId) {
    Write-Host "PERHATIAN: belum ada ID ekstensi. Muat dulu folder extension\chromium"
    Write-Host "di chrome://extensions (mode pengembang), catat ID-nya, lalu jalankan lagi:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File Install-NativeHost-Exe.ps1 -ExtensionId <ID>"
    $ExtensionId = "EXTENSION_ID_DARI_BROWSER"
}
$chromium = @{
    name = $name; description = "Yukii Download Manager"; path = $hostExe
    type = "stdio"; allowed_origins = @("chrome-extension://$ExtensionId/")
} | ConvertTo-Json -Depth 4
$firefox = @{
    name = $name; description = "Yukii Download Manager"; path = $hostExe
    type = "stdio"; allowed_extensions = @("ydm@yukii.id")
} | ConvertTo-Json -Depth 4
$chromiumPath = Join-Path $dir "$name.chromium.json"
$firefoxPath = Join-Path $dir "$name.firefox.json"
Set-Content -Encoding UTF8 $chromiumPath $chromium
Set-Content -Encoding UTF8 $firefoxPath $firefox

$bases = @(
    "HKCU:\Software\Google\Chrome\NativeMessagingHosts",
    "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts",
    "HKCU:\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
    "HKCU:\Software\Chromium\NativeMessagingHosts"
)
foreach ($b in $bases) {
    $k = Join-Path $b $name
    New-Item -Force $k | Out-Null
    Set-ItemProperty $k "(Default)" $chromiumPath
}
$k = "HKCU:\Software\Mozilla\NativeMessagingHosts\$name"
New-Item -Force $k | Out-Null
Set-ItemProperty $k "(Default)" $firefoxPath
Write-Host "Native host .exe terdaftar untuk Chrome, Edge, Brave, Chromium, Firefox."
Write-Host "Host: $hostExe"
