@echo off
setlocal
cd /d "%~dp0"

if exist "dist\ReactorPWR.exe" (
  rem CWD = raiz del repo para que logs/ no caiga dentro de dist/
  start "" /D "%~dp0" "%~dp0dist\ReactorPWR.exe"
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
