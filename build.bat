@echo off
echo [Data Intelligence PRO] EXE Build Script for Windows
echo --------------------------------------------------
echo 1. Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo 2. Starting PyInstaller Build...
pyinstaller --noconsole --onefile --name "DataIntelligencePRO" --collect-all lxml --hidden-import win32com.client --hidden-import pythoncom app/main.py

echo.
echo 3. Build Finished! Check the 'dist' folder.
pause
