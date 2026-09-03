@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Zainstaluj Python 3 ze strony python.org i zaznacz "Add Python to PATH".
  pause
  exit /b 1
)
py -m pip install -r requirements.txt
py photo_scroller_v2.py
