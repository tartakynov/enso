from enso.events import EventManager
from enso.commands import CommandManager
from enso.contrib.scriptotron.tracker import ScriptTracker

def load():
    import sys
    from enso.contrib.scriptotron.ensoapi import EnsoApi
    sys.path.append(EnsoApi().get_enso_commands_folder())

    ScriptTracker.install( EventManager.get(),
                           CommandManager.get() )
