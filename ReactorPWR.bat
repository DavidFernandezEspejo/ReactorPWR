@echo off
setlocal
cd /d "%~dp0"

if exist "dist\ReactorPWR.exe" (
  start "" "%~dp0dist\ReactorPWR.exe"
  exit /b 0
)

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=py -3"
)

set PYTHONPATH=%~dp0
%PYTHON% run_reactor.py
endlocal
