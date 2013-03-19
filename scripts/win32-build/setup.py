from distutils.core import setup
import py2exe
import sys
import os

try:
	try:
		import py2exe.mf as modulefinder
	except ImportError:
		import modulefinder
	import win32com, sys
	for p in win32com.__path__[1:]:
		modulefinder.AddPackagePath("win32com", p)
	for extra in ["win32com.shell"]: #,"win32com.mapi"
		__import__(extra)
		m = sys.modules[extra]
		for p in m.__path__[1:]:
			modulefinder.AddPackagePath(extra, p)
except ImportError:
	pass

commands = []
for root, _, files in os.walk("scripts/commands/"):
	for f in files:
		commands.append(os.path.join(root, f))

sys.path.append("enso/platform/win32")
setup(
	name	= "Enso",
	version	= "1.0",
	author	= "Enso Community",
	windows	= [ { "script" : "scripts/run_enso.py", "icon_resources" : [(1, "media/images/enso.ico")] } ],
	data_files = [(".", ["media/images/enso.ico", "media/fonts/GenI102.TTF", "media/fonts/GenR102.TTF", "media/fonts/OFL.txt"]), ("commands", commands)],
	options =
	{
		"py2exe": {
			"includes" : ["win32process", "win32file", "ctypes.wintypes", "glob", "webbrowser", "platform", "enso.contrib.*"],
			"dll_excludes" : ["mswsock.dll", "powrprof.dll", "msimg32.dll"]
		}
	}
)

if os.path.isfile("dist/enso.exe"): 
	os.remove("dist/enso.exe")
os.rename("dist/run_enso.exe", "dist/enso.exe")