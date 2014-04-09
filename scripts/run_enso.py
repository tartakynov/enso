#! /usr/bin/env python

import os
import sys
import time
import threading
import logging
import pythoncom
import win32gui
import win32con
from win32com.shell import shell, shellcon

import enso
from enso.messages import displayMessage
from enso.platform.win32.taskbar import SysTrayIcon
from optparse import OptionParser

ENSO_DIR = os.path.realpath(os.path.dirname(sys.argv[0]))
ENSO_EXECUTABLE = os.path.join(ENSO_DIR, "enso.exe")
ENSO_ICON = os.path.join(ENSO_DIR, "enso.ico")

options = None
systrayIcon = None

def tray_on_enso_quit(systray):
    enso.stop()

def tray_on_enso_about(systray):
    displayMessage(enso.config.ABOUT_BOX_XML)

def tray_on_enso_help(systray):
    pass


def tray_on_enso_exec_at_startup(systray, get_state = False):
    startup_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
    assert os.path.isdir(startup_dir)

    link_file = os.path.join(startup_dir, "Enso.lnk")

    if get_state:
        return os.path.isfile(link_file)
    else:
        if not os.path.isfile(link_file):
            try:
                pythoncom.CoInitialize()
            except:
                # already initialized.
                pass

            shortcut = pythoncom.CoCreateInstance(
                shell.CLSID_ShellLink,
                None,
                pythoncom.CLSCTX_INPROC_SERVER,
                shell.IID_IShellLink
            )

            shortcut.SetPath(ENSO_EXECUTABLE)
            shortcut.SetWorkingDirectory(ENSO_DIR)
            shortcut.SetIconLocation(ENSO_ICON, 0)

            shortcut.QueryInterface( pythoncom.IID_IPersistFile ).Save(
                link_file, 0 )
            try:
                pythoncom.CoUnInitialize()
            except:
                pass

            displayMessage(u"<p><command>Enso</command> will be automatically executed at system startup</p><caption>enso</caption>")
        else:
            os.remove(link_file)
            displayMessage(u"<p><command>Enso</command> will not start at system startup</p><caption>enso</caption>")



def systray(enso_config):
    """ Tray-icon handling code. This have to be executed in its own thread
    """
    global systrayIcon
    
    logging.info( "Enso tray icon '%s'." % ENSO_ICON )

    systrayIcon = SysTrayIcon(
            ENSO_ICON,
            "Enso open-source",
            None,
            on_quit = tray_on_enso_quit)
    systrayIcon.on_about = tray_on_enso_about
    systrayIcon.on_doubleclick = tray_on_enso_about
    systrayIcon.add_menu_item("Execute on &startup", tray_on_enso_exec_at_startup)
    systrayIcon.main_thread()

def process_options(argv):
    version = '1.0'
    usageStr = "%prog [options]\n\n"
    parser = OptionParser(usage=usageStr, version="%prog " + version)
    #parser.add_option("-l", "--log", action="store", dest="logfile", type="string", help="log output into auto-rotated log-file", metavar="FILE")
    #TODO: Implement more command line args
    parser.add_option("-l", "--log-level", action="store", dest="loglevel", default="ERROR", help="logging level (CRITICAL, ERROR, INFO, WARNING, DEBUG)")
    parser.add_option("-c", "--console", action="store_true", dest="show_console", default=False, help="Console messages")
    parser.add_option("-t", "--no-tray", action="store_false", dest="show_tray_icon", default=True, help="Hide tray icon")
    opts, args = parser.parse_args(argv)
    return opts, args


def main(argv = None):
    global options

    opts, args = process_options(argv)
    options = opts

    loglevel = {
        'CRITICAL' : logging.CRITICAL,
        'ERROR' : logging.ERROR,
        'INFO' : logging.INFO,
        'WARNING' : logging.WARNING,
        'DEBUG' : logging.DEBUG
        }[opts.loglevel]

    if opts.show_console:
        print "Showing console"
        logging.basicConfig( level = loglevel )
    else:
        print "Hiding console"
        print "Logging into '%s'" % os.path.join(ENSO_DIR, "enso.log")
        sys.stdout = open("stdout.log", "w", 0) #NullDevice()
        sys.stderr = open("stderr.log", "w", 0) #NullDevice()
        logging.basicConfig(
            filename = os.path.join(ENSO_DIR, "enso.log"),
            level = loglevel )

    if loglevel == logging.DEBUG:
        print opts
        print args

    ensorcPath = os.path.join(ENSO_DIR, ".ensorc")
    if os.path.exists( ensorcPath ):
        logging.info( "Loading '%s'." % ensorcPath )
        contents = open( ensorcPath, "r" ).read()
        compiledContents = compile( contents + "\n", ensorcPath, "exec" )
        exec compiledContents in {}, {}

    if opts.show_tray_icon:
        # Execute tray-icon code in separate thread
        threading.Thread(target = systray, args = (enso.config,)).start()

    enso.run()
    win32gui.PostMessage(systrayIcon.hwnd, win32con.WM_CLOSE, 0, 0)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
   

# vim:set tabstop=4 shiftwidth=4 expandtab: