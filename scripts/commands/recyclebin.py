import os
import pythoncom
import logging
import win32api
import win32con
import win32file
from win32com.shell import shell, shellcon

from enso.messages import displayMessage

my_documents_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, 0, 0)
LEARN_AS_DIR = os.path.join(my_documents_dir, u"Enso's Learn As Open Commands")
RECYCLE_BIN_LINK = os.path.join(LEARN_AS_DIR, "recycle bin.lnk")

if not os.path.isfile(RECYCLE_BIN_LINK):
    recycle_shortcut = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
    )
    #recycle_shortcut.QueryInterface( pythoncom.IID_IPersistFile ).Load(
    #    os.path.join(LEARN_AS_DIR, "recycle.lnk"))
    #print recycle_shortcut.GetArguments()
    #print recycle_shortcut.GetIconLocation()
    #print recycle_shortcut.GetDescription()
    #print recycle_shortcut.GetIDList()
    #print recycle_shortcut.GetPath(shell.SLGP_UNCPRIORITY)
    recycle_shortcut.SetPath("")
    recycle_shortcut.SetWorkingDirectory("")
    recycle_shortcut.SetIDList(['\x1f\x00@\xf0_d\x81P\x1b\x10\x9f\x08\x00\xaa\x00/\x95N'])
    recycle_shortcut.QueryInterface( pythoncom.IID_IPersistFile ).Save(
        RECYCLE_BIN_LINK, 0 )


def _get_recycle_bins():
    #logging.debug(repr(win32api.GetLogicalDrives()))
    drives = win32api.GetLogicalDriveStrings()
    #logging.debug(repr(drives.split("\0")))
    bin_info = []
    for drive in drives.split("\0"):
        drive_type = win32file.GetDriveType(drive)
        if drive_type in (
            win32file.DRIVE_FIXED,
            win32file.DRIVE_RAMDISK
            #win32file.DRIVE_REMOVABLE
            ):
            # Detect SUBSTed volume and ignore it
            try:
                volume_mapping = win32file.QueryDosDevice(drive[:2])
                if volume_mapping.startswith("\\??\\"):
                    break
            except:
                pass
            try:
                size, files = shell.SHQueryRecycleBin(drive)
                bin_info.append((drive, size, files))
                logging.debug(drive + str(drive_type))
            except Exception, e:
                log.error(e)
    return bin_info


def cmd_recycle_bin(ensoapi, operation = "show"):
    """ Recycle bin {operation} """
    if operation.startswith("show"):
        #drive = operation.split(" ")[1]
        ensoapi.display_message("Opening Recycle Bin")
        """
        win32api.ShellExecute(
            0,
            "open",
            "explorer.exe " ,
            "/root,::{645FF040-5081-101B-9F08-00AA002F954E} ",
            None,
            1)
        """
        try:
            os.startfile(os.path.normpath(RECYCLE_BIN_LINK))
        except:
            pass
    elif operation.startswith("delete "):
        drive = operation.split(" ")[1]
        # SHERB_NOCONFIRMATION
        #    No dialog box confirming the deletion of the objects will be displayed.
        # SHERB_NOPROGRESSUI
        #    No dialog box indicating the progress will be displayed.
        # SHERB_NOSOUND
        #    No sound will be played when the operation is complete.
        print drive
        res = shell.SHEmptyRecycleBin(0, drive, 0)
    elif operation == "info":
        bins_info = _get_recycle_bins()
        if len(bins_info) > 0:
            infos = []
            for drive, size, files in bins_info:
                if files == 0 and size == 0:
                    infos.append(u"<command>%s</command> empty" % drive)
                else:
                    if size < 1024:
                        size_hr = "%.2f B" % size
                    elif size < 1024*1024:
                        size_hr = "%.2f kB" % (size / 1024)
                    elif size < 1024*1024*1024:
                        size_hr = "%.2f MB" % (size / 1024 / 1024)
                    elif size < 1024*1024*1024*1024:
                        size_hr = "%.2f GB" % (size / 1024 / 1024 / 1024)
                    elif size < 1024*1024*1024*1024*1024:
                        size_hr = "%.2f TB" % (size / 1024 / 1024 / 1024 / 1024)
                    infos.append(u"<command>%s</command> %s in %d files" % (drive, size_hr, files))
                msg = u"<p>%s</p><caption>Recycle bin(s) information</caption>" % u"</p><p>".join(infos)
            displayMessage(msg)
        else:
            ensoapi.display_message(u"There appears to be no recycle bins on this system")

cmd_recycle_bin.valid_args = ['info']
cmd_recycle_bin.valid_args.extend([('delete %s' % drive) for drive, _, _ in _get_recycle_bins()])

# vim:set tabstop=4 shiftwidth=4 expandtab:
