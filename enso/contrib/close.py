import re
import os
import win32gui
import win32con
import win32process
import win32api
import xml.sax.saxutils
import time
import atexit
from SendKeys import SendKeys as sendkeys

from enso.commands import CommandManager, CommandObject
from enso.events import EventManager

import logging
import ctypes
from ctypes import *
from ctypes.wintypes import HWND #, RECT, POINT

MULTIWINAPP = [ # (class_name, title, process_exe)
        (r"Chrome_XPFrame", None, None),
        (r"MozillaUIWindowClass", None, r"firefox\.exe"),
        (r"KMeleon Browser Window", None, None),
        (r"IEFrame", None, r"iexplore\.exe"),
        (r"Chrome_WidgetWin_0", None, r"chrom(e|ium)\.exe"),
        (r"OpWindow", r".* - Opera$", r"opera\.exe"),
        (r"SWT_Window0", None, r"eclipse\.exe"),
        (r"Vim", None, r"gvim\.exe"),
        (r"XLMAIN", None, r"excel\.exe")
    ]


def _stdcall(dllname, restype, funcname, *argtypes):
    # a decorator for a generator.
    # The decorator loads the specified dll, retrieves the
    # function with the specified name, set its restype and argtypes,
    # it then invokes the generator which must yield twice: the first
    # time it should yield the argument tuple to be passed to the dll
    # function (and the yield returns the result of the call).
    # It should then yield the result to be returned from the
    # function call.
    def decorate(func):
        api = getattr(WinDLL(dllname), funcname)
        api.restype = restype
        api.argtypes = argtypes

        def decorated(*args, **kw):
            iterator = func(*args, **kw)
            nargs = iterator.next()
            if not isinstance(nargs, tuple):
                nargs = (nargs,)
            try:
                res = api(*nargs)
            except Exception, e:
                return iterator.throw(e)
            return iterator.send(res)
        return decorated
    return decorate


def nonzero(result):
    # If the result is zero, and GetLastError() returns a non-zero
    # error code, raise a WindowsError
    if result == 0 and GetLastError():
        raise WinError()
    return result


@_stdcall("user32", c_int, "GetWindowTextLengthW", HWND)
def GetWindowTextLength(hwnd):
    yield nonzero((yield hwnd,))


@_stdcall("user32", c_int, "GetWindowTextW", HWND, c_wchar_p, c_int)
def GetWindowText(hwnd):
    len = GetWindowTextLength(hwnd)+1
    buf = create_unicode_buffer(len)
    nonzero((yield hwnd, buf, len))
    yield buf.value


class _ForegroundWindowCommand( CommandObject ):
    """
    Command helper class used to handle command-action over
    foreground (active) window

    - It sets _foreground_window and _foreground_window_title
    variables on quasimode-start for usage in the command
    help-text
    """

    NAME = None

    def __init__( self ):
        super( _ForegroundWindowCommand, self ).__init__()

        self._foreground_window = None
        self._foreground_window_title = None

        EventManager.get().registerResponder( self.on_quasimode_start, "startQuasimode" )
        atexit.register(self.__finalize)


    def __finalize(self):
        EventManager.get().removeResponder(self.on_quasimode_start)


    def run( self ):
        assert self._foreground_window is not None
        raise NotImplementedError


    def on_quasimode_start(self):
        win = win32gui.GetForegroundWindow()
        self._foreground_window = win
        self._foreground_window_title = xml.sax.saxutils.escape(
            self._shorten_text(
                GetWindowText(win), 60))

        assert self._foreground_window is not None


    def _shorten_text(self, text, max_length):
        return u"%s..." % text[:max_length] if len(text) > max_length else text


    def _set_foregeound_window(self, hwnd):
        try:
            if win32gui.IsIconic(hwnd):
                logging.info("Restoring window")
                win32gui.ShowWindow(hwnd, 1)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception, e:
            logging.error(e)
            if e[0] == 0:
                time.sleep(0.2)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    return True
                except Exception, e:
                    logging.error(e)
                    time.sleep(0.2)
                    try:
                        win32gui.BringWindowToTop(hwnd)
                        return True
                    except Exception, e:
                        logging.error(e)
            elif e[0] == 2:
                pass
        return False



class QuitCommand( _ForegroundWindowCommand ):
    """
    Quit foreground application.
    """
    NAME = "quit"

    def __init__( self ):
        super( QuitCommand, self ).__init__()


    def on_quasimode_start(self):
        super( QuitCommand, self ).on_quasimode_start()
        self.setDescription( u"Quit application \u201c%s\u201d" % self._foreground_window_title )

        assert self._foreground_window is not None


    def run( self ):
        assert self._foreground_window is not None

        win32gui.PostMessage(self._foreground_window, win32con.WM_SYSCOMMAND, win32con.SC_CLOSE, None)



def _is_multiwindow_app(win):
    for test_class, test_title, test_process in MULTIWINAPP:
        match = None
        if test_class:
            class_name = win32gui.GetClassName(win)
            match = re.match(test_class, class_name, re.IGNORECASE)
            if not match:
                #logging.debug("class NOT matched: %s on %s" % (test_class, class_name))
                continue
            else:
                pass
                #logging.debug("class matched: %s on %s" % (test_class, class_name))

        if test_title:
            title = GetWindowText(win)
            match = re.match(test_title, title, re.IGNORECASE)
            if not match:
                #logging.debug("title NOT matched: %s on %s" % (test_title, title))
                continue
            else:
                pass
                #logging.debug("title matched: %s on %s" % (test_title, title))

        if test_process:
            _, process_id = win32process.GetWindowThreadProcessId(win)
            proc_handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, True, process_id)
            process_exe = os.path.basename(win32process.GetModuleFileNameEx(proc_handle, 0)).lower()
            match = re.match(test_process, process_exe, re.IGNORECASE)
            if not match:
                #logging.debug("process NOT matched: %s on %s" % (test_process, process_exe))
                continue
            else:
                pass
                #logging.debug("process matched: %s on %s" % (test_process, process_exe))
        
        if match:
            return True

    return False


class CloseCommand( _ForegroundWindowCommand ):
    """
    Close foreground window or tab.
    """
    NAME = "close"


    def __init__( self ):
        super( CloseCommand, self ).__init__()


    def on_quasimode_start(self):
        super( CloseCommand, self ).on_quasimode_start()
        if _is_multiwindow_app(self._foreground_window):
            desc = u"Close tab \u201c%s\u201d" % self._foreground_window_title
        else:
            desc = u"Close window \u201c%s\u201d" % self._foreground_window_title
        self.setDescription( desc )


    def run( self ):
        assert self._foreground_window is not None

        class_name = win32gui.GetClassName(self._foreground_window)
        #win32gui.PostMessage(win.GetHwnd(), win32con.WM_SYSCOMMAND, win32con.SC_CLOSE, None)
        #sendkeys("^{F4}")

        """
        from ctypes import windll
        topwin = windll.user32.GetTopWindow(self._foreground_window)
        print self._foreground_window, GetWindowText(self._foreground_window)
        print topwin, GetWindowText(topwin)
        return

        if re.match("^(Chrome_XPFrame|MozillaWindowClass|KMeleon Browser Window|SWT_Window0|Vim)$", class_name):
            if self._set_foregeound_window(self._foreground_window):
                sendkeys("^w")
            return
        """


        """
        if class_name == "SWT_Window0" and process_exe == "eclipse.exe":
            if self._set_foregeound_window(self._foreground_window):
                sendkeys("^w")
            return
        """
        if self._set_foregeound_window(self._foreground_window):
            if class_name == "ConsoleWindowClass":
                win32gui.SendMessage(self._foreground_window, win32con.WM_CLOSE, 0, None)
            elif _is_multiwindow_app(self._foreground_window):
                sendkeys("^{F4}") # Ctrl+F4
            else:
                sendkeys("%{F4}") # Alt+F4
        #win32gui.SendMessage(self._foreground_window, win32con.WM_CLOSE, None, None)





def load():
    CommandManager.get().registerCommand(
        CloseCommand.NAME,
        CloseCommand()
        )
    CommandManager.get().registerCommand(
        QuitCommand.NAME,
        QuitCommand()
        )

# vim:set tabstop=4 shiftwidth=4 expandtab:    
