# Copyright (c) 2008, Pavel Vitis
# All rights reserved.
#
# blackdaemon@seznam.cz
# http://blackdaemon.no-ip.org/wiki/projects:enso

# ----------------------------------------------------------------------------
#
#   Enso service plugin
#   Windows XP/Vista only
#
#   This plugin is a helper service for Enso developers. It provides native
#   directory and file monitoring service.
#   It is able to provide list of added / removed / modified
#   directories and/or files to the registered callback function.
#   Since it uses native Win32 notifications API, it uses very low resources
#   and actually notifies immediatelly after file has been changed.
#
#   It provide DirectoryWatcher singleton.
#
#   Example usage, registering callback function 'filename_updated' to be
#   called everytime 'filename' file changes:
#
#      from enso.contrib.directory_watcher import DirectoryWatcher
#
#      def filename_updated(dir, added, deleted, modified):
#          print "Directory %s modified" % dir
#          print "Files added: " + repr(added)
#          print "Files deleted: " + repr(deleted)
#          print "Files modified: " + repr(modified)
#
#      watcher = DirectoryWatcher.get()
#      watcher.register_handler('filename', filename_updated)
#
#
#   Unregistering callback function:
#
#      watcher.unregister_handler(filename_updated)
#
#
#   Unregistering directory with all callback functions registered on it:
#
#      watcher.unregister_directory(dir_name)
#
#
#   Unregistering specific directory and callback function:
#
#      watcher.unregister_directory(dir_name, callback_func)
# ----------------------------------------------------------------------------


import Queue
import atexit
import logging
import os
import threading
import time
import win32con
import win32event
import win32file


def _functions_equal(func1, func2):
    """ 
    Compare two function signatures and return True if match.
    It means that after the module holding function is reloaded
    and function's pointer changes, it is still recognized as
    the same function as before.

    """
    assert func1 is not None, "func1 parameter must not be None"
    assert func2 is not None, "func2 parameter must not be None"

    # Function name must match
    if func1.func_name != func2.func_name:
        return False
    # Function module must match
    if func1.__module__ != func2.__module__:
        return False
    f1_arg_cnt = func1.func_code.co_argcount
    f2_arg_cnt = func2.func_code.co_argcount
    # Function parameter count must match
    if f1_arg_cnt != f2_arg_cnt:
        return False
    # Function parameter names must match
    if func1.func_code.co_varnames[:f1_arg_cnt] != func2.func_code.co_varnames[:f2_arg_cnt]:
        return False
    return True



class _DirMonitor:
    def __init__(self, path):
        if os.path.isdir(path):
            self.dir = path
            self.file = None
        elif os.path.isfile(path):
            self.dir = os.path.dirname(path)
            self.file = os.path.basename(path)
            self.filemtime = os.path.getmtime(path)
        else:
            self.dir = path
            self.file = None

        self.handlers = []
        self.change_handle = None
        self.path_contents = os.listdir(self.dir)

    def add_handler(self, handler):
        self.handlers.append(handler)

    def remove_handler(self, handler):
        for func in self.handlers:
            if _functions_equal(func, handler):
                del self.handlers[self.handlers.index(func)]

    def get_handlers(self):
        return self.handlers

    def set_change_handle(self, change_handle):
        self.change_handle = change_handle

    def get_change_handle(self):
        return self.change_handle

    def get_dir(self):
        return self.dir

    def get_filename(self):
        return self.file

    def reload_file_changes(self):
        new_path_contents = os.listdir(self.dir)
        files_added = [f for f in new_path_contents if not f in self.path_contents]
        files_deleted = [f for f in self.path_contents if not f in new_path_contents]
        self.path_contents = new_path_contents

        if (self.file is not None
            and not self.file in files_deleted
            and not self.file in files_added):
            try:
                time.sleep(0.2)
                new_mtime = os.path.getmtime(os.path.join(self.dir, self.file))
                if new_mtime != self.filemtime:
                    self.filemtime = new_mtime
                    return [], [], [self.file]
                else:
                    return [], [], []
            except Exception, e:
                logging.error(e)
                return [], [], []
        else:
            return files_added, files_deleted, []


class _DirectoryWatchingThread(threading.Thread):

    MONITOR_ADD = "add"
    MONITOR_REMOVE = "remove"


    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.queue = Queue.Queue()
        self.__success = False
        self.__retval = None
        self.__is_running = False


    def run(self):
        self.__is_running = True
        self.__change_handles = None
        self.__dirs = {}
        try:
            while self.__is_running:
                self.__refresh_requests()

                if self.__change_handles is None:
                    for monitor in self.__dirs.values():
                        # Newly added
                        if monitor.get_change_handle() is None:
                            monitor.set_change_handle(
                                win32file.FindFirstChangeNotification (
                                    monitor.get_dir(),
                                    0,
                                    win32con.FILE_NOTIFY_CHANGE_FILE_NAME
                                )
                            )
                    # Refresh change handlers cache
                    print "Refreshing change-handles cache"
                    self.__change_handles = {}
                    for monitor in [
                        monitor
                        for monitor in self.__dirs.values()
                        if monitor.get_change_handle()]:
                        self.__change_handles[monitor.get_change_handle()] = monitor
                    print self.__change_handles
                #old_path_contents = os.listdir (self.path_to_watch)
                if len(self.__change_handles) > 0:
                    result = win32event.WaitForMultipleObjects(self.__change_handles.keys(), False, 500)
                else:
                    result = win32con.WAIT_FAILED

                if (result >= win32con.WAIT_OBJECT_0) and (result <= win32con.WAIT_OBJECT_0 + len(self.__change_handles) - 1):
                    changed_handle = self.__change_handles.keys()[result]
                    #print changed_handle
                    monitor = self.__change_handles[changed_handle]
                    #print monitor.get_dir()
                    #print monitor.get_handlers()
                    added, deleted, modified = monitor.reload_file_changes()
                    if len(added) > 0 or len(deleted) > 0 or len(modified) > 0:
                        logging.info(monitor.get_handlers())
                        self.__serve_handlers(monitor, added, deleted, modified)

                    win32file.FindNextChangeNotification(changed_handle)
        finally:
            for monitor in self.__dirs.values():
                if monitor.get_change_handle():
                    win32file.FindCloseChangeNotification(monitor.get_change_handle())
                    monitor.set_change_handle(None)
        self.__success = True
        logging.info("Directory watcher finished")


    def stop(self):
        self.__is_running = False


    def add_monitor(self, dir, handler):
        self.queue.put((self.MONITOR_ADD, dir, handler))


    def remove_monitor(self, dir, handler):
        self.queue.put((self.MONITOR_REMOVE, dir, handler))


    def __serve_handlers(self, monitor, added_files, deleted_files, modified_files):
        for handler in monitor.get_handlers():
            try:
                handler(monitor.get_dir(), added_files, deleted_files, modified_files)
            except Exception, e:
                logging.error(e)


    def __refresh_requests(self):
        try:
            while True:
                op, dir, handler = self.queue.get_nowait()
                try:
                    if op == self.MONITOR_ADD:
                        if not dir in self.__dirs:
                            monitor = _DirMonitor(dir)
                            self.__dirs[dir] = monitor
                        else:
                            monitor = self.__dirs[dir]
                        if not handler in monitor.get_handlers():
                            monitor.add_handler(handler)
                            self.__change_handles = None
                            logging.info("Adding " + repr(dir) + "; " + repr(handler))
                    elif op == self.MONITOR_REMOVE:
                        if dir in self.__dirs:
                            monitor = self.__dirs[dir]
                            monitor.remove_handler(handler)
                            self.__change_handles = None
                            logging.info("Removing " + repr(dir) + "; " + repr(handler))
                finally:
                    self.queue.task_done()
        except Queue.Empty:
            pass


class DirectoryWatcher:
    """
    Directory watcher service
    Provides DirectoryWatcher singleton

    Usage:
    from directory_watcher import DirectoryWatcher
    dw = DirectoryWatcher.get()
    dw.register_handler(some_dir, handler_function)

    dw.unregister_handler(handler_function)
    or
    dw.unregister_directory(some_dir, handler_function)
    or
    dw.unregister_directory(some_dir)
    """
    __instance = None

    @classmethod
    def get(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance


    def __init__(self):
        self.watched_dirs = {}
        self.watcher_thread = _DirectoryWatchingThread()
        self.watcher_thread.setDaemon(True)
        self.watcher_thread.start()

        atexit.register(self.stop)


    def stop(self):
        if self.watcher_thread:
            self.watcher_thread.stop()
            self.watcher_thread.join()
            del self.watcher_thread
            self.watcher_thread = None

     
    def is_registered(self, dir, handler):
        """ Check if the directory/function pair is already registered.
        If func1 is registered and func2 has the same signature it is 
        considered as already registered. 
        This is to ensure that if module holding the registered function gets
        reloaded, the function is still recognized even that the pointers doesn't 
        match anymore (module.func1 != <reloaded>module.func1).
        """
        assert dir is not None
        assert hasattr(handler, "__call__"), "handler parameter must be callable"

        dir = os.path.normcase(os.path.normpath(dir))
        if dir not in self.watched_dirs:
            return False
        for func in self.watched_dirs[dir]:
            if _functions_equal(func, handler):
                return True
        return False


    def register_handler(self, dir, handler, force = False):
        #assert os.path.isdir(dir), "dir parameter must be existing directory"
        assert hasattr(handler, "__call__"), "handler parameter must be callable"
        assert force or not self.is_registered(dir, handler), "directory/handler pair already registered"

        dir = os.path.normcase(os.path.normpath(dir))

        if not dir in self.watched_dirs:
            self.watched_dirs[dir] = [handler,]
        else:
            handlers = self.watched_dirs[dir]
            for func in handlers:
                if _functions_equal(func, handler):
                    if force:
                        del handlers[handlers.index(func)]
                        self.watcher_thread.remove_monitor(dir, handler)
                    else:
                        assert False, "directory/handler pair already registered"
            self.watched_dirs[dir].append(handler)

        self.watcher_thread.add_monitor(dir, handler)
        #print "handler for '%s' dir registered: '%s'" % (dir, handler.__name__)


    def unregister_handler(self, handler):
        assert hasattr(handler, "__call__"), "handler parameter must be callable"

        for dir, handlers in self.watched_dirs.items():
            for func in handlers:
                if _functions_equal(func, handler):
                    del handlers[handlers.index(func)]
                    self.watcher_thread.remove_monitor(dir, func)


    def unregister_directory(self, dir, handler = None):
        dir = os.path.normcase(os.path.normpath(dir))
        if dir in self.watched_dirs:
            if handler is None:
                for h in self.watched_dirs[dir].values():
                    self.watcher_thread.remove_monitor(dir, h)
                del self.watched_dirs[dir]
            else:
                handlers = self.watched_dirs[dir]
                for func in handlers:
                    if _functions_equal(func, handler):
                        del handlers[handlers.index(func)]
                        self.watcher_thread.remove_monitor(dir, func)


"""
def simple_handler(dir, added, deleted, modified):
    print "Directory changed: %s" % dir
    if len(added) > 0:
        print "Added files: " + repr(added)
    if len(deleted) > 0:
        print "Deleted files: " + repr(deleted)
    if len(modified) > 0:
        print "Modified files: " + repr(modified)


if hasattr(enso.config, "directory_watcher") and enso.config.directory_watcher:
    enso.config.directory_watcher.stop()
    del enso.config.directory_watcher
    enso.config.directory_watcher = None

enso.config.directory_watcher =
enso.config.directory_watcher.register_handler("C:\\Documents and Settings\\pavel\\Favorites\\Desktop.ini", simple_handler)
enso.config.directory_watcher.register_handler("C:\\Documents and Settings\\pavel\\Local Settings\\Application Data\\Google\\Chrome\\User Data\\Default", simple_handler)
"""

# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    DirectoryWatcher.get()

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:    
