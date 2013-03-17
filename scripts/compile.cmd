@echo off
set PYTHONPATH=%PYTHONPATH%;..\
cd..
scons && python scripts\setup.py py2exe && pause
