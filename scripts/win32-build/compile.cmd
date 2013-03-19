@echo off
set PYTHONPATH=%PYTHONPATH%;..\..\
cd ..\..\
scons && python scripts\win32-build\setup.py py2exe && pause
