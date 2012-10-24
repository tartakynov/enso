#! /usr/bin/env python

import os
import logging

import enso

if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO )

    # TODO: os.getenv( "HOME" ) only works 'out-of-the-box' on
    # unix; we need to do something different, preferably
    # in platform-specific backends.
    homeDir = os.getenv( "HOME" )
    if homeDir:
        ensorcPath = os.path.join( homeDir, ".ensorc" )
        if os.path.exists( ensorcPath ):
            logging.info( "Loading '%s'." % ensorcPath )
            contents = open( ensorcPath, "r" ).read()
            compiledContents = compile( contents, ensorcPath, "exec" )
            exec compiledContents in {}, {}

    enso.run()
