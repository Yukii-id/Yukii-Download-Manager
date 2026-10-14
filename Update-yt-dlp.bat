@echo off
rem Update yt-dlp YDM - dijalankan manual atau oleh Task Scheduler mingguan.
cd /d "%~dp0"
python -m ydm.updater --update-now >> "data\update-ytdlp.log" 2>&1
