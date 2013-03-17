###############################################################################
#  (c) 2008, Pavel Vitis
#  blackdaemon@seznam.cz
#
#  Enso Prioritizer
#      Windows XP/Vista only
#  Change process priority of Enso as follows:
#    * On Enso startup, 30 seconds highest priority
#    * After 30 seconds, set back to normal priority
#    * on quasimode-start set to highest priority
#    * on quasimode-end set back to normal priority
#
#  To install prioritizer:
#      1. copy prioritizer.py into enso/contrib directory
#      2. Edit .ensorc file and add following on the beginning:
#       
#         import enso.contrib.prioritizer
#         enso.contrib.prioritizer.load()
#
###############################################################################


###############################################################################
#  Imports
###############################################################################

import threading
import win32api
import win32con
import win32process

from enso.events import EventManager
from enso import input

###############################################################################
#  Constants
###############################################################################

# Priority of high demand
# Do not set this to win32process.REALTIME_PRIORITY_CLASS!
HIGH_PRIORITY = win32process.HIGH_PRIORITY_CLASS

# Priority of normal (idle) mode
# Setting this to win32process.IDLE_PRIORITY_CLASS is not recommended
# You may consider setting to win32process.ABOVE_NORMAL_PRIORITY_CLASS
IDLE_PRIORITY = win32process.NORMAL_PRIORITY_CLASS

# Time in seconds, how long after Enso startup to switch back to normal mode
ON_ENSO_READY_TIMEOUT = 30.0

###############################################################################
#  Code
###############################################################################

on_enso_ready_timer = None


def set_priority(prio):
    """ Set priority of current Enso process """
    our_pid = win32api.GetCurrentProcessId()
    our_handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, our_pid)
    win32process.SetPriorityClass(our_handle, prio)


def clear_on_enso_ready_timer():
    """ Cancel on-enso-ready timer """
    global on_enso_ready_timer
    if on_enso_ready_timer:
        on_enso_ready_timer.cancel()
        on_enso_ready_timer = None


def  on_enso_ready():
    """ Set normal priority on Enso ready """
    print "ENSO IS READY, SETTING IDLE PRIORITY"
    set_priority(IDLE_PRIORITY)


def  on_quasimode_start():
    """ Set highest priority on quasimode-start """
    print "ENSO QUASIMODE START, SETTING HIGH PRIORITY"
    set_priority(HIGH_PRIORITY)


def  on_quasimode_end():
    """ Set highest priority on quasimode-end """
    print "ENSO QUASIMODE END, SETTING IDLE PRIORITY"
    set_priority(IDLE_PRIORITY)


def on_quasimode_key(eventType, keyCode):
    """ Event reponder function to detect quasimode-start/end event """
    if eventType == input.EVENT_KEY_QUASIMODE:
        clear_on_enso_ready_timer()
        if keyCode == input.KEYCODE_QUASIMODE_START:
            on_quasimode_start()
        elif keyCode == input.KEYCODE_QUASIMODE_END:
            on_quasimode_end()

# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    # Set maximum priority on start
    print "SETTING INITIAL HIGH PRIORITY"
    set_priority(HIGH_PRIORITY)

    # Setup timer to switch back to normal priority after some time
    global on_enso_ready_timer
    on_enso_ready_timer = threading.Timer(ON_ENSO_READY_TIMEOUT, on_enso_ready)
    on_enso_ready_timer.start()

    # Schedule normal priority after init is completed
    # TODO: Not reliable
    #EventManager.get().registerResponder(on_enso_ready, "init")

    # Register key-event reponder for detecting quasimode changes
    EventManager.get().registerResponder(on_quasimode_key, "key")


# vim:set tabstop=4 shiftwidth=4 expandtab:
