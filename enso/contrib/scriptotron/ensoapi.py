import xml.sax.saxutils

from enso.messages import displayMessage
from enso import selection

class EnsoApi(object):
    """
    A simple facade to Enso's functionality for use by commands.
    """

    def display_message(self, msg, caption=None):
        """
        Displays the given message, with an optional caption.  Both
        parameters should be unicode strings.
        """

        if not isinstance(msg, basestring):
            msg = unicode(msg)

        msg = xml.sax.saxutils.escape(msg)
        xmltext = "<p>%s</p>" % msg
        if caption:
            caption = xml.sax.saxutils.escape(caption)
            xmltext += "<caption>%s</caption>" % caption
        return displayMessage(xmltext)

    def get_selection(self):
        """
        Retrieves the current selection and returns it as a
        selection dictionary.
        """

        return selection.get()

    def set_selection(self, seldict):
        """
        Sets the current selection to the contents of the given
        selection dictionary.

        Alternatively, if a string is provided instead of a
        dictionary, the current selection is set to the unicode
        contents of the string.
        """

        if isinstance(seldict, basestring):
            seldict = { "text" : unicode(seldict) }
        return selection.set(seldict)
