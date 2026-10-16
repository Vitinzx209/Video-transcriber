@echo off
setlocal
cd /d "%~dp0"
title Transcritor local

if not exist ".venv\Scripts\python.exe" (
  echo Antes, execute setup.cmd.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" video-transcriber.py
pause
