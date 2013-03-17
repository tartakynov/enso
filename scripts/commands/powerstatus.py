import win32api
import win32con
import ctypes
import struct


def cmd_battery_status(ensoapi):
    """ Show internal battery status """

    ACSTATUS_OFFLINE = 0
    ACSTATUS_ONLINE = 1
    ACSTATUS_UNKNOWN = 255
    BATTERYFLAG_HIGH = 1 # more than 66%
    BATTERYFLAG_NORMAL = 0 # more than 66%
    BATTERYFLAG_LOW = 2 # less than 33%
    BATTERYFLAG_CRITICAL = 4 # less than 5%
    BATTERYFLAG_CHARGING = 8
    BATTERYFLAG_NOBATTERY = 128
    BATTERYFLAG_UNKNOWNSTATUS = 255
    
    status = struct.Struct("BBBBll")
    #    print status.size
    buffer = ctypes.create_string_buffer(status.size)
    ctypes.windll.kernel32.GetSystemPowerStatus(buffer)
    #    print status.unpack_from(buffer)
    (ac_line_status, 
        battery_flag, 
        battery_life_percent, 
        _, 
        battery_life_time, 
        battery_full_life_time) = status.unpack_from(buffer)
    
    #print battery_flag
    if battery_flag == BATTERYFLAG_NOBATTERY:
        ensoapi.display_message(u"This system has no battery attached.")
        return

    #print battery_life_time/60/60

    battery_status = (
        "good" if battery_flag == BATTERYFLAG_HIGH 
        else "normal" if battery_flag == BATTERYFLAG_NORMAL
        else "low" if battery_flag == BATTERYFLAG_LOW 
        else "critical" if battery_flag == BATTERYFLAG_CRITICAL 
        else "charging" if battery_flag == BATTERYFLAG_CHARGING 
        else "unknown")

    ac_status = (
        "Online, " if ac_line_status == ACSTATUS_ONLINE 
        else "Offline, " if ac_line_status == ACSTATUS_OFFLINE
        else "")

    if battery_life_time != -1:
        hours = battery_life_time / 60 / 60
        minutes = battery_life_time / 60 - hours * 60
        lifetime = "%d:%02dh " % (hours, minutes)
    else:
        lifetime = ""

    if ac_line_status == ACSTATUS_ONLINE:
        msg = u"Online, %(status)s%(percentage)s" % { 
            "status" : "charging " if battery_flag == BATTERYFLAG_CHARGING else "",
            "percentage" : "(%d%%)" % battery_life_percent if battery_flag == BATTERYFLAG_CHARGING 
                else "%d%%" % battery_life_percent
            }
    else:
        msg = u"%(acstatus)s %(lifetime)s(%(percentage)d%%) remaining" % { 
            "percentage" : battery_life_percent, 
            "acstatus" : ac_status,
            "batterystatus" : battery_status,
            "lifetime" : lifetime
            }
    ensoapi.display_message(msg, u"Battery status")

# vi:set ff=unix tabstop=4 shiftwidth=4 expandtab:
