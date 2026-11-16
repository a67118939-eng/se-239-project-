"""Shared constants for the ticket booking system (used by server, client and tests).

Owner: Zain Osama Alkatmah (Protocol and Data Lead)
"""

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
ENCODING = "utf-8"

# A message is one line, at most this many bytes (not counting the newline).
MAX_LINE = 256

# The event has 20 seats: A1..A5, B1..B5, C1..C5, D1..D5.
ROWS = "ABCD"
SEATS_PER_ROW = 5
ALL_SEATS = [f"{row}{number}" for row in ROWS for number in range(1, SEATS_PER_ROW + 1)]

# One user may hold at most this many seats at the same time.
MAX_SEATS_PER_USER = 3

# Error codes sent to the client after the word ERROR.
BAD_COMMAND = "BAD_COMMAND"
LINE_TOO_LONG = "LINE_TOO_LONG"
NOT_LOGGED_IN = "NOT_LOGGED_IN"
ALREADY_LOGGED_IN = "ALREADY_LOGGED_IN"
BAD_USERNAME = "BAD_USERNAME"
USERNAME_TAKEN = "USERNAME_TAKEN"
UNKNOWN_SEAT = "UNKNOWN_SEAT"
SEAT_TAKEN = "SEAT_TAKEN"
LIMIT_REACHED = "LIMIT_REACHED"
SERVER_ERROR = "SERVER_ERROR"
