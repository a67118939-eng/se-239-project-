"""Command-line client for the ticket booking server.

Usage:  python client.py [--host 127.0.0.1] [--port 5000]

Commands once logged in:
  list            show the seat map
  book <seat>     book a seat, e.g.  book B3
  mine            show the seats you have booked
  quit            leave
  raw <text>      send text to the server exactly as typed (to test bad input)
  help            show this list

Owner: Ahmed Hejazi (Client Lead)
"""

import argparse
import socket

import config

HELP = """Commands:
  list          show the seat map
  book <seat>   book a seat, e.g. book B3
  mine          show the seats you have booked
  quit          leave
  raw <text>    send text to the server exactly as typed
  help          show this list"""

FRIENDLY_ERRORS = {
    config.BAD_COMMAND: "The server did not understand that command.",
    config.LINE_TOO_LONG: "That message was too long.",
    config.NOT_LOGGED_IN: "You must log in first.",
    config.ALREADY_LOGGED_IN: "You are already logged in.",
    config.BAD_USERNAME: "Usernames must be 3-15 letters, digits or underscores.",
    config.USERNAME_TAKEN: "That username is already in use. Pick another one.",
    config.UNKNOWN_SEAT: "That seat does not exist (seats are A1 to D5).",
    config.SEAT_TAKEN: "Sorry, that seat is already taken.",
    config.LIMIT_REACHED: f"You already have {config.MAX_SEATS_PER_USER} seats, the maximum.",
    config.SERVER_ERROR: "The server had a problem with that request.",
}


class Connection:
    """A TCP connection that sends one line and reads one line back."""

    def __init__(self, host, port):
        self._sock = socket.create_connection((host, port), timeout=10)
        self._sock.settimeout(None)
        self._buffer = b""

    def request(self, line):
        self._sock.sendall(line.encode(config.ENCODING) + b"\n")
        return self._read_line()

    def _read_line(self):
        while b"\n" not in self._buffer:
            data = self._sock.recv(1024)
            if not data:
                raise ConnectionError("the server closed the connection")
            self._buffer += data
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode(config.ENCODING, "replace").strip()

    def close(self):
        try:
            self._sock.close()
        except OSError:
            pass


def show_seats(tokens):
    """Print the seat map from tokens like ['A1:FREE', 'A2:BOOKED', ...]."""
    state = {}
    for token in tokens:
        seat, _, status = token.partition(":")
        state[seat] = status
    print("\n       " + "".join(f"{n:^6}" for n in range(1, config.SEATS_PER_ROW + 1)))
    for row in config.ROWS:
        cells = ""
        for n in range(1, config.SEATS_PER_ROW + 1):
            mark = "X" if state.get(f"{row}{n}") == "BOOKED" else " "
            cells += f"{'[' + mark + ']':^6}"
        print(f"   {row}   {cells}")
    free = sum(1 for status in state.values() if status == "FREE")
    print(f"\n   [ ] free   [X] booked      {free} of {len(state)} seats free\n")


def show_reply(reply):
    """Print a server reply in a readable way."""
    parts = reply.split()
    if len(parts) >= 2 and parts[0] == "OK":
        if parts[1] == "SEATS":
            show_seats(parts[2:])
        elif parts[1] == "BOOKED":
            print(f"Booked seat {parts[2]}.")
        elif parts[1] == "MYBOOKING":
            if parts[2:] == ["NONE"]:
                print("You have not booked any seats yet.")
            else:
                print("Your seats: " + ", ".join(parts[2:]))
        elif parts[1] == "BYE":
            print("Goodbye.")
        else:
            print(reply)
    elif len(parts) == 2 and parts[0] == "ERROR":
        print(FRIENDLY_ERRORS.get(parts[1], reply))
    else:
        print(reply)


def translate(text):
    """Turn what the user typed into a protocol line (or None if there is nothing to send)."""
    words = text.split()
    if not words:
        return None
    word = words[0].lower()
    if word == "raw":
        return text.split(None, 1)[1] if len(words) > 1 else None
    if word in ("list", "seats"):
        return "LIST"
    if word == "book" and len(words) == 2:
        return "BOOK " + words[1]
    if word in ("mine", "mybooking"):
        return "MYBOOKING"
    if word in ("quit", "exit"):
        return "QUIT"
    return text  # let the server answer with its own error


def log_in(connection):
    """Ask for a username until the server accepts one. Returns the name, or None to give up."""
    while True:
        try:
            name = input("Choose a username: ").strip()
        except EOFError:
            return None
        if not name:
            continue
        reply = connection.request("LOGIN " + name)
        if reply.startswith("OK"):
            return name
        show_reply(reply)


def main():
    parser = argparse.ArgumentParser(description="Ticket booking client")
    parser.add_argument("--host", default=config.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    args = parser.parse_args()

    try:
        connection = Connection(args.host, args.port)
    except OSError as problem:
        print(f"Could not connect to {args.host}:{args.port}: {problem}")
        return 1
    print(f"Connected to {args.host}:{args.port}")

    try:
        name = log_in(connection)
        if name is None:
            return 0
        print(f"Welcome, {name}!\n{HELP}")
        while True:
            try:
                text = input("> ")
            except (EOFError, KeyboardInterrupt):
                text = "quit"
            if text.strip().lower() == "help":
                print(HELP)
                continue
            line = translate(text)
            if line is None:
                continue
            reply = connection.request(line)
            show_reply(reply)
            if reply == "OK BYE":
                break
    except ConnectionError as problem:
        print(f"Connection lost: {problem}")
        return 1
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
