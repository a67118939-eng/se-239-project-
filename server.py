"""The ticket booking server: accepts TCP connections and runs one thread per client.

Usage:  python server.py [--host 127.0.0.1] [--port 5000]
Use --host 0.0.0.0 to let other computers on the same network connect.

Owner: Mohammed Badr Alsakran (Server Lead)
"""

import argparse
import logging
import socket
import threading

import config
from booking import BookingSystem
from protocol import Session, error, handle_request

log = logging.getLogger("server")


class TicketServer:
    def __init__(self, host=config.DEFAULT_HOST, port=config.DEFAULT_PORT, system=None):
        self.host = host
        self.port = port
        self.system = system if system is not None else BookingSystem()
        self._listener = None
        self._stop = threading.Event()
        self._clients = set()
        self._clients_lock = threading.Lock()

    def bind(self):
        """Create the listening socket. After this, self.port is the real port."""
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind((self.host, self.port))
        self._listener.listen()
        # A timeout lets the loop notice shutdown (and Ctrl+C on Windows).
        self._listener.settimeout(1.0)
        self.port = self._listener.getsockname()[1]
        log.info("listening on %s:%s", self.host, self.port)

    def serve_forever(self):
        """Accept clients until shutdown(). Each client gets its own thread."""
        while not self._stop.is_set():
            try:
                conn, addr = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break  # listening socket was closed by shutdown()
            conn.settimeout(None)
            threading.Thread(target=self._handle_client, args=(conn, addr),
                             daemon=True).start()

    def shutdown(self):
        self._stop.set()
        if self._listener is not None:
            self._listener.close()
        with self._clients_lock:
            clients = list(self._clients)
        for conn in clients:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
        log.info("server stopped")

    @staticmethod
    def _send(conn, text):
        conn.sendall((text + "\n").encode(config.ENCODING))

    def _handle_client(self, conn, addr):
        """Read lines from one client, answer each one, until it quits or drops."""
        with self._clients_lock:
            self._clients.add(conn)
        session = Session()
        buffer = b""
        skipping = False  # True while throwing away the rest of an over-long line
        log.info("connected: %s:%s", *addr)
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break  # client closed the connection
                buffer += data
                while True:
                    newline = buffer.find(b"\n")
                    if newline == -1:
                        if len(buffer) > config.MAX_LINE:
                            if not skipping:
                                self._send(conn, error(config.LINE_TOO_LONG))
                                skipping = True
                            buffer = b""
                        break
                    line, buffer = buffer[:newline], buffer[newline + 1:]
                    if skipping:
                        skipping = False  # this was the end of the over-long line
                        continue
                    if len(line) > config.MAX_LINE:
                        self._send(conn, error(config.LINE_TOO_LONG))
                        continue
                    try:
                        reply, close = handle_request(self.system, session, line)
                    except Exception:
                        log.exception("error while handling a request")
                        reply, close = error(config.SERVER_ERROR), False
                    log.info("%s <- %r  -> %s", session.username or addr[1],
                             line.decode(config.ENCODING, "replace"), reply[:60])
                    self._send(conn, reply)
                    if close:
                        return
        except OSError as problem:
            log.info("connection lost (%s:%s): %s", addr[0], addr[1], problem)
        except Exception:
            log.exception("unexpected error with client %s:%s", *addr)
        finally:
            if session.logged_in:
                self.system.logout(session.username)
            with self._clients_lock:
                self._clients.discard(conn)
            try:
                conn.close()
            except OSError:
                pass
            log.info("disconnected: %s:%s (%s)", addr[0], addr[1], session.username or "not logged in")


def main():
    parser = argparse.ArgumentParser(description="Ticket booking server")
    parser.add_argument("--host", default=config.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(threadName)s] %(message)s")
    server = TicketServer(args.host, args.port)
    try:
        server.bind()
    except OSError as problem:
        print(f"Cannot start the server on {args.host}:{args.port}: {problem}")
        return 1
    print("Server running. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
