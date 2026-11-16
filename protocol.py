"""The message format: parsing client lines, validating them, and building replies.

All message handling is kept in this one file. The server only reads lines from the
socket and calls handle_request(); this module decides what each message means.

Owner: Zain Osama Alkatmah (Protocol and Data Lead)
"""

import re

import config
from booking import BookingError

_USERNAME = re.compile(r"[A-Za-z0-9_]{3,15}")

# command word -> number of arguments it needs
_ARGUMENT_COUNT = {"LOGIN": 1, "LIST": 0, "BOOK": 1, "MYBOOKING": 0, "QUIT": 0}


class ProtocolError(Exception):
    """The line could not be understood. `code` is the error code for the client."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class Session:
    """What the server remembers about one connection: who is logged in on it."""

    def __init__(self):
        self.username = None

    @property
    def logged_in(self):
        return self.username is not None


def ok(*parts):
    return " ".join(("OK",) + parts)


def error(code):
    return "ERROR " + code


def parse_line(raw):
    """Turn one received line (bytes, without the newline) into (COMMAND, [args]).

    Raises ProtocolError(BAD_COMMAND) for anything that is not a known command with
    the right number of arguments.
    """
    try:
        text = raw.decode(config.ENCODING)
    except UnicodeDecodeError:
        raise ProtocolError(config.BAD_COMMAND)
    words = text.split()
    if not words:
        raise ProtocolError(config.BAD_COMMAND)
    command = words[0].upper()
    args = words[1:]
    if command not in _ARGUMENT_COUNT or len(args) != _ARGUMENT_COUNT[command]:
        raise ProtocolError(config.BAD_COMMAND)
    return command, args


def valid_username(name):
    return _USERNAME.fullmatch(name) is not None


def handle_request(system, session, raw_line):
    """Handle one request line. Returns (reply_text, close_connection).

    `system` is the shared BookingSystem and `session` is this connection's Session.
    Always returns exactly one reply, so the client never has to guess.
    """
    try:
        command, args = parse_line(raw_line)
    except ProtocolError as problem:
        return error(problem.code), False

    if command == "QUIT":
        return ok("BYE"), True

    if command == "LOGIN":
        if session.logged_in:
            return error(config.ALREADY_LOGGED_IN), False
        name = args[0]
        if not valid_username(name):
            return error(config.BAD_USERNAME), False
        try:
            system.login(name)
        except BookingError as problem:
            return error(problem.code), False
        session.username = name
        return ok("LOGIN", name), False

    if not session.logged_in:
        return error(config.NOT_LOGGED_IN), False

    if command == "LIST":
        pairs = [f"{seat}:{state}" for seat, state in system.list_seats()]
        return ok("SEATS", *pairs), False

    if command == "BOOK":
        seat = args[0].upper()
        try:
            system.book_seat(session.username, seat)
        except BookingError as problem:
            return error(problem.code), False
        return ok("BOOKED", seat), False

    # MYBOOKING is the only command left.
    seats = system.my_bookings(session.username)
    return ok("MYBOOKING", *(seats if seats else ["NONE"])), False
