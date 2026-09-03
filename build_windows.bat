@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo      PHOTO SCROLLER V2 - BUDOWANIE EXE
echo ==================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo Nie znaleziono Pythona.
  echo Zainstaluj Python 3 ze strony python.org i zaznacz "Add Python to PATH".
  pause
  exit /b 1
)

py -m pip install --upgrade pip
if errorlevel 1 goto :error
py -m pip install -r requirements.txt
if errorlevel 1 goto :error

py -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name PhotoScrollerV2 ^
  --collect-all tkinterdnd2 ^
  photo_scroller_v2.py
if errorlevel 1 goto :error

echo.
echo ==================================================
echo GOTOWE!
echo Plik programu:
echo %CD%\dist\PhotoScrollerV2.exe
echo ==================================================
explorer "%CD%\dist"
pause
exit /b 0

:error
echo.
echo Wystapil blad podczas budowania programu.
pause
exit /b 1
