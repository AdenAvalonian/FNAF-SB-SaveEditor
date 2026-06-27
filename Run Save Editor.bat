@echo off
REM Launches the FNAF SB Save Editor. Requires Python 3 with Tkinter installed.
python "%~dp0save_editor.py"
if errorlevel 1 (
  echo.
  echo Could not start. Make sure Python 3 is installed and on your PATH.
  echo Download it from https://www.python.org/downloads/ ^(tick "Add Python to PATH"^).
  pause
)
