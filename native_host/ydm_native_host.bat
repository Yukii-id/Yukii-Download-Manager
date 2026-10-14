@echo off
rem Wrapper Native Host YDM: browser memanggil berkas .bat ini (Windows)
rem yang meneruskan stdio ke skrip Python.
python "%~dp0ydm_native_host.py" %*
