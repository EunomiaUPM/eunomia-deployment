@echo off
rem Run the eunomia CLI on Windows: eunomia.cmd <command>
rem Calls eunomia.ps1 without depending on the PowerShell ExecutionPolicy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0eunomia.ps1" %*
exit /b %ERRORLEVEL%
