"""Small tools shared by the tests: a bare-bones test client and a server starter.

Owner: Mohammad Asaad Alrefai (Testing and Demo Lead)
"""

import os
import socket
import sys
import threading

# Let the tests import server.py, booking.py, ... from the project folder.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from server import TicketServer  # noqa: E402


class TestClient:
    """A minimal client for tests: send a line, get a line back."""

    __test__ = False  # not a test class (keeps test runners from collecting it)

    def __init__(self, port, host="127.0.0.1"):
        self.sock = socket.create_connection((host, port), timeout=5)
        self._buffer = b""

    def send_raw(self, data):
        self.sock.sendall(data)

    def read_line(self):
        while b"\n" not in self._buffer:
            data = self.sock.recv(1024)
            if not data:
                raise ConnectionError("server closed the connection")
            self._buffer += data
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode("utf-8", "replace")

    def request(self, line):
        self.send_raw(line.encode("utf-8") + b"\n")
        return self.read_line()

    def login(self, name):
        return self.request("LOGIN " + name)

    def closed_by_server(self):
        """True if the server has closed this connection (recv returns nothing)."""
        try:
            return self.sock.recv(1024) == b""
        except OSError:
            return True

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def start_server():
    """Start a server on a free port in a background thread. Call .shutdown() when done."""
    server = TicketServer("127.0.0.1", 0)
    server.bind()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
