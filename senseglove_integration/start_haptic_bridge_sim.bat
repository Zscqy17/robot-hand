@echo off
setlocal
cd /d "%~dp0.."
call ".venv\Scripts\activate.bat"
python senseglove_integration\haptic_bridge.py --simulate --no-robot
endlocal
