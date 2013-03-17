import logging
import os
import types

from enso.commands.manager import CommandAlreadyRegisteredError
from enso.contrib.scriptotron.tracebacks import TracebackCommand
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.contrib.scriptotron.events import EventResponderList
from enso.contrib.scriptotron import adapters
from enso.contrib.scriptotron import cmdretriever
from enso.contrib.scriptotron import ensoapi
from enso.contrib.scriptotron import concurrency

import enso.system

# These should be defined in a platform-specific back end
SCRIPTS_FILE_NAME = os.path.expanduser("~/.ensocommands")
SCRIPTS_FOLDER_NAME = os.path.join(
    enso.system.SPECIALFOLDER_ENSOLOCAL, "commands")

class ScriptCommandTracker:
    def __init__( self, commandManager, eventManager ):
        self._cmdExprs = []
        self._cmdMgr = commandManager
        self._genMgr = concurrency.GeneratorManager( eventManager )
        self._qmStartEvents = EventResponderList(
            eventManager,
            "startQuasimode",
            self._onQuasimodeStart
            )

    @safetyNetted
    def _callHandler( self, handler ):
        result = handler()
        if isinstance( result, types.GeneratorType ):
            self._genMgr.add( result )

    def _onQuasimodeStart( self ):
        for handler in self._qmStartEvents:
            self._callHandler( handler )

    def clearCommands( self, cmdExprExt = None ):
	if cmdExprExt:
            for cmdExpr in cmdExprExt:
                self._cmdMgr.unregisterCommand( cmdExpr )
	else:		    
            for cmdExpr in self._cmdExprs:
                self._cmdMgr.unregisterCommand( cmdExpr )
            self._cmdExprs = []
            self._qmStartEvents[:] = []
            self._genMgr.reset()

    def _registerCommand( self, cmdObj, cmdExpr ):
        try:
            self._cmdMgr.registerCommand( cmdExpr, cmdObj )
            self._cmdExprs.append( cmdExpr )
        except CommandAlreadyRegisteredError:
            logging.warn( "Command already registered: %s" % cmdExpr )

    def registerNewCommands( self, commandInfoList ):
        for info in commandInfoList:
            if hasattr( info["func"], "on_quasimode_start" ):
                self._qmStartEvents.append( info["func"].on_quasimode_start )
            cmd = adapters.makeCommandFromInfo(
                info,
                ensoapi.EnsoApi(),
                self._genMgr
                )
            self._registerCommand( cmd, info["cmdExpr"] )

class ScriptTracker:
    def __init__( self, eventManager, commandManager ):
        self._scriptCmdTracker = ScriptCommandTracker( commandManager,
                                                       eventManager )
        self._scriptFilename = SCRIPTS_FILE_NAME
        self._scriptFolder = SCRIPTS_FOLDER_NAME
        self._lastMods = {}
        self._registerDependencies()
	self._commandsInFile = {}
        # Call it now, otherwise there is a delay on first quasimode invocation
        self._updateScripts()

        eventManager.registerResponder(
            self._updateScripts,
            "startQuasimode"
            )

        commandManager.registerCommand( TracebackCommand.NAME,
                                        TracebackCommand() )

    @classmethod
    def install( cls, eventManager, commandManager ):
        cls( eventManager, commandManager )

    @safetyNetted
    def _getGlobalsFromSourceCode( self, text, filename ):
        allGlobals = {}
        code = compile( text, filename, "exec" )
        exec code in allGlobals
        return allGlobals

    def _getCommandFiles( self ):
        try:
            commandFiles = [
              os.path.join(self._scriptFolder,x)
              for x in os.listdir(self._scriptFolder)
              if x.endswith(".py")
            ]
        except:
            commandFiles = []
        return commandFiles

    def _reloadPyScripts( self, files = None ):
        self._scriptCmdTracker.clearCommands( files )
        commandFiles = [self._scriptFilename]
        if files:
            commandFiles = commandFiles + files
            print "Files to reload: ", commandFiles
        else:
            commandFiles = commandFiles + self._getCommandFiles()

        logging.debug(commandFiles)

        for f in commandFiles:
            try:
                text = open( f, "r" ).read()
            except:
                continue

            allGlobals = self._getGlobalsFromSourceCode(
                text,
                f
                )

            if allGlobals is not None:
                infos = cmdretriever.getCommandsFromObjects( allGlobals )
		#print f, infos
                self._scriptCmdTracker.registerNewCommands( infos )
                self._registerDependencies( allGlobals )
		self._commandsInFile[f] = infos


    def _registerDependencies( self, allGlobals = None ):
        baseDeps = [ self._scriptFilename ] + self._getCommandFiles()

        if allGlobals:
            # Find any other files that the script may have executed
            # via execfile().
            extraDeps = [
                obj.func_code.co_filename
                for obj in allGlobals.values()
                if ( (hasattr(obj, "__module__")) and
                     (obj.__module__ is None) and
                     (hasattr(obj, "func_code")) )
                ]
        else:
            extraDeps = []

        self._fileDependencies = list( set(baseDeps + extraDeps) )

    def _updateScripts( self ):
        shouldReload = False
        filesToReload = {}
        for fileName in self._fileDependencies:
            if os.path.exists( fileName ):
                lastMod = os.stat( fileName ).st_mtime
                if lastMod != self._lastMods.get(fileName):
                    self._lastMods[fileName] = lastMod
                    filesToReload[fileName] = lastMod
                    shouldReload = True

        for fileName in self._getCommandFiles():
            if fileName not in self._fileDependencies:
                self._fileDependencies.append(fileName)
                self._lastMods[fileName] = os.stat( fileName ).st_mtime
                filesToReload[fileName] = lastMod
                shouldReload = True

        if shouldReload:
            #self._reloadPyScripts(filesToReload.keys())
	    self._reloadPyScripts()

