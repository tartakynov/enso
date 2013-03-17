import enso.config

from enso.commands import CommandManager, CommandObject
from enso.commands.factories import GenericPrefixFactory
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.contrib.scriptotron import ensoapi
from enso.messages import displayMessage


class EnsoUndoCache:
    items = {}

    __instance = None

    @classmethod
    def get(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        pass

    def push(self, id, command, values):
        if not hasattr(command, "__call__"):
            print "Command is not callable"
        self.items[id] = (command, values)

    def pop(self, id, default = None):
        values = self.items.get(id, default)
        del self.items[id]
        return values

    def get_items(self):
        return self.items.keys()


# ----------------------------------------------------------------------------
# The Undo command
# ---------------------------------------------------------------------------
class UndoCommand(CommandObject):
    """
    Implementation of the 'undo' command.
    """

    NAME = "undo {what}"
    HELP = "command"
    HELP_TEXT = "command"
    PREFIX = "undo "
    DESCRIPTION = HELP_TEXT
    DESCRIPTION_TEXT = HELP_TEXT

    def __init__( self, parameter = None ):
        """
        Initializes the undo command.
        """
        
        print "UndoCommand.__init__()"
        CommandObject.__init__( self )

        self.parameter = parameter

        """
        if parameter != None:
            self.setDescription( u"Performs a Google web search for "
                                 u"\u201c%s\u201d." % parameter )
        """
        self.setDescription(" sfsdfsfsf")
        self.setHelp("asdsf ")


    def run( self ):
        """
        Runs the google command.
        """
        if not self.parameter:
            return

        uc = EnsoUndoCache.get()

        print "Parameter: '%s'" % self.parameter
        command, values = uc.pop(self.parameter)
        print command
        print values
        if hasattr(command, "undo"):
            if command.undo(ensoapi.EnsoApi(), self.parameter, values):
                displayMessage(u"<p>Command <command>%s</command> has been undone.</p>" % self.parameter)



def cmd_undo(ensoapi, what):
    uc = EnsoUndoCache.get()
    command, values = uc.pop(what)
    command.undo(values)
    cmd_undo.valid_args = enso.config.undo_cache.get_items()
    
try:
    print enso.config.undo_cache
except:
    enso.config.undo_cache = EnsoUndoCache.get()

cmd_undo.valid_args = enso.config.undo_cache.get_items()


def set_undo(id, command, values):
    uc = EnsoUndoCache.get()
    uc.push(id, command, values)
    cmd_undo.valid_args = uc.get_items()


class UndoCommandFactory( GenericPrefixFactory ):
    """
    Generates a "undo {what}" command.
    """

    NAME = "undo {what}"
    HELP = "command"
    HELP_TEXT = "command"
    PREFIX = "undo "
    DESCRIPTION = HELP_TEXT
    DESCRIPTION_TEXT = HELP_TEXT

    def _generateCommandObj( self, parameter = None ):
        print "Instantiating Undo command"
        cmd = UndoCommand( parameter )
        print "Undo command registered"
        return cmd

    @safetyNetted
    def update(self):
        print "Undo command update()"
        uc = EnsoUndoCache.get()
        self.setPostfixes(uc.get_items())

# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    CommandManager.get().registerCommand(
        UndoCommandFactory.NAME,
        UndoCommandFactory()
        )

# vim:set tabstop=4 shiftwidth=4 expandtab:
