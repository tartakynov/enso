# Copyright (c) 2008, Humanized, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Enso nor the names of its contributors may
#       be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Humanized, Inc. ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Humanized, Inc. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ----------------------------------------------------------------------------
#
#   enso
#
# ----------------------------------------------------------------------------

webuiServer = None
eventManager = None
started = False

def showWelcomeMessage():
    msgXml = config.OPENING_MSG_XML
    if msgXml != None:
        messages.displayMessage( msgXml )

def run():
    """
    Initializes and runs Enso.
    """
    import logging
    from enso.events import EventManager
    from enso.quasimode import Quasimode
    from enso import events, plugins, config, quasimode, webui
    global started, webuiServer, eventManager

    eventManager = EventManager.get()
    Quasimode.install( eventManager )
    plugins.install( eventManager )

    if not started:
        eventManager.registerResponder( showWelcomeMessage, "init" )
        try:
            started = True
            webuiServer = webui.start(eventManager)
            eventManager.run()
        except KeyboardInterrupt, e:
            webuiServer.stop()
        except Exception, e:
            webuiServer.stop()
            logging.error(e)

def stop():
    """
    Performs safe stop.
    """
    global started
    if started:
        webuiServer.stop()
        eventManager.stop()
        started = False
