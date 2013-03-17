import threading
import Queue
import cgi
import urllib
import os
import socket
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import logging
import enso.messages
from enso.contrib.scriptotron import cmdretriever
from enso.contrib.scriptotron.tracebacks import safetyNetted

class myhandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server, queue):
        self.queue = queue
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        if self.path == "/install.js":
            jspath = os.path.join(os.path.split(__file__)[0], "enso-install.js")
            fp = open(jspath)
            js = fp.read()
            fp.close()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
            self.end_headers()
            self.wfile.write(js)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write("404 Not Found")


    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })
        url = form.getfirst("url", None)
        if url:
            self.queue.put(url)
            self.send_response(200)
            self.end_headers()
            self.wfile.write("""OK""")
        else:
            self.send_response(401)
            self.end_headers()
            self.wfile.write("""Bad Request""")


class myhttpd(HTTPServer):

    def __init__(self, server_address, RequestHandlerClass, queue):
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.queue = queue


    def server_bind(self):
        HTTPServer.server_bind(self)
        self.socket.settimeout(1)
        self.run = True


    def get_request(self):
        while self.run:
            try:
                sock, addr = self.socket.accept()
                sock.settimeout(None)
                return (sock, addr)
            except socket.timeout:
                if not self.run:
                    raise socket.error


    def finish_request(self, request, client_address):
        # overridden from SocketServer.TCPServer
        logging.info("Finish request called")
        self.RequestHandlerClass(request, client_address, self, self.queue)


    def stop(self):
        self.run = False


    def serve_forever(self):
        """ Override serve_forever to handle shutdown. """
        while self.run:
            self.handle_request()



class Httpd(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        self.server = myhttpd(('localhost', 31750), myhandler, self.queue)
        self.server.serve_forever()

    def stop(self):
        logging.info("Stopping the WebUI server")
        self.server.stop()


def displayMessage(msg):
    enso.messages.displayMessage("<p>%s</p>" % msg)


@safetyNetted
def get_commands_from_object(text, filename):
    allGlobals = {}
    code = compile( text, filename, "exec" )
    exec code in allGlobals
    return cmdretriever.getCommandsFromObjects(allGlobals)


def install_command_from_url(command_url):
    try:
        fp = urllib.urlopen(command_url)
    except:
        msg = "Couldn't install that command"
        displayMessage(msg)
        return

    text = fp.read()
    fp.close()

    # Normalize newlines to "\n"
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = text.split("\n")
    if len(lines) < 3:
        msg = u"There was no command to install!"
        displayMessage(msg)
        return
    while lines[0].strip() == "":
        lines.pop(0)
    command_file_name = command_url.split("/")[ - 1]
    if not command_file_name.endswith(".py"):
        msg = u"Couldn't install this command <command>%s<.command>" % command_file_name
        displayMessage(msg)
        return
    from enso.contrib.scriptotron.tracker import SCRIPTS_FOLDER_NAME as cmd_folder
    command_file_path = os.path.expanduser(os.path.join(cmd_folder, command_file_name))
    shortname = os.path.splitext(command_file_name)[0]
    if os.path.exists(command_file_path):
        msg = u"You already have a command named <command>%s</command>" % shortname
        displayMessage(msg)
        return

    commands = get_commands_from_object(text, command_file_path)
    if commands:
        installed_commands = [x["cmdName"] for x in commands]
    else:
        installed_commands = []

    if len(installed_commands) == 1:
        install_message = u"<command>%s</command> is now a command" % installed_commands[0]
    elif len(installed_commands) > 1:
        install_message = u"<command>%s</command> are now commands" % u"</command>, <command>".join(installed_commands)
    else:
        install_message = u"Problem installing command"

    # Use binary mode for writing so endlines are not converted to "\r\n" on win32
    fp = open(command_file_path, "wb")
    fp.write(text)
    fp.close()
    displayMessage(install_message)


commandq = Queue.Queue()

def pollqueue(ms):
    try:
        command_url = commandq.get(False, 0)
    except Queue.Empty:
        return

    # FIXME: here we should check to see if it's OK to install this command!
    install_command_from_url(command_url)


def start(eventManager):
    logging.info("Starting WebUI")
    httpd_server = Httpd(commandq)
    httpd_server.setDaemon(True)
    httpd_server.start()
    eventManager.registerResponder(pollqueue, "timer")
    return httpd_server
