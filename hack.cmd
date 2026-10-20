@echo off
rem Lanza hack.ps1 sin depender de la ExecutionPolicy de Windows.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0hack.ps1" %*
exit /b %ERRORLEVEL%
