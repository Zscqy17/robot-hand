@echo off
setlocal
cd /d "%~dp0.."
call ".venv\Scripts\activate.bat"
python senseglove_integration\test_senseglove.py --simulate
endlocal
