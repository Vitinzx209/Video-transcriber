@echo off
setlocal
cd /d "%~dp0"
title Transcritor local - instalar

set "PY_CMD="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
  python --version >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)
if not defined PY_CMD (
  echo Python 3 nao encontrado. Instale em https://www.python.org/downloads/windows/ e marque "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  call %PY_CMD% -m venv .venv
  if errorlevel 1 ( echo Falha ao criar o ambiente. & pause & exit /b 1 )
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 ( echo Falha ao instalar as dependencias. & pause & exit /b 1 )

set "FF_DIR="
for /d %%D in ("%~dp0ffmpeg*") do if exist "%%D\bin\ffmpeg.exe" set "FF_DIR=%%D"
where ffmpeg >nul 2>nul
if not errorlevel 1 goto ffmpeg_ok
if defined FF_DIR goto ffmpeg_ok

echo.
echo FFmpeg nao encontrado. Baixando para esta pasta (cerca de 100 MB)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg-download.zip'; Expand-Archive -LiteralPath 'ffmpeg-download.zip' -DestinationPath '.' -Force; Remove-Item 'ffmpeg-download.zip'"
for /d %%D in ("%~dp0ffmpeg*") do if exist "%%D\bin\ffmpeg.exe" set "FF_DIR=%%D"
if not defined FF_DIR (
  echo Nao foi possivel baixar o FFmpeg. Instale com:  winget install Gyan.FFmpeg
  echo ou baixe em https://www.gyan.dev/ffmpeg/builds/ e extraia a pasta ao lado deste script.
  pause
  exit /b 1
)

:ffmpeg_ok
echo FFmpeg OK.

echo.
echo Pronto. Agora execute start.cmd e deixe a janela aberta.
pause
