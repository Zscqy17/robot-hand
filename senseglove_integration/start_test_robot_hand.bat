@echo off
setlocal
cd /d "%~dp0.."
call ".venv\Scripts\activate.bat"
python senseglove_integration\test_robot_hand.py
endlocal
