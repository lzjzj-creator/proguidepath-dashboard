@echo off
title Resume Platform
cd /d "%~dp0"
echo Starting Resume Platform...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
