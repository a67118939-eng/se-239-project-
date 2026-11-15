# Ticket Booking System (SE239, team Engineers)

A TCP client-server ticket booking system written in Python 3 (standard library only).
One server holds 20 seats (A1 to D5) for one event. Several clients connect at once, log in
with a username, view the seats and book them. A seat is never given to two clients, even if
two requests arrive at the same moment.

## Run it

You need Python 3.8 or newer. Open a terminal in the project folder.

```
python server.py                      # terminal 1: start the server (port 5000)
python client.py                      # terminal 2, 3, 4...: one terminal per client
```

On Windows, if `python` is not found, use `py` instead.

To connect from another computer on the same network, start the server with
`python server.py --host 0.0.0.0` and the clients with `python client.py --host <server-ip>`.

Client commands: `list`, `book <seat>` (e.g. `book B3`), `mine`, `quit`, `raw <text>`, `help`.

## Run the tests

```
python -m unittest discover -s tests -v
python tests/selfcheck.py            # PASS/FAIL for each required feature
```

Race demo against a running server (10 fake clients all try to book A1; exactly one wins):

```
python tests/stress_same_seat.py --clients 10 --seat A1
```

## Files and owners

GitHub repository owner: Ahmed Hejazi (roles below are unchanged).

| File | What it does | Owner |
|---|---|---|
| `server.py` | Accepts connections, one thread per client, error handling, shutdown | Mohammed Badr Alsakran |
| `booking.py` | Seat table, the lock, booking rules, online users | Abdulaziz Al Thunyan |
| `client.py` | Command-line client | Ahmed Hejazi |
| `protocol.py`, `config.py` | Message format, parsing, validation, error codes, shared constants | Zain Osama Alkatmah |
| `tests/` | Tests, race test script | Mohammad Asaad Alrefai |
| `docs/` | Proposal, design document, test checklist, AI-use log | everyone |

## Messages (one line each, ending in a newline)

Client to server: `LOGIN <username>`, `LIST`, `BOOK <seat>`, `MYBOOKING`, `QUIT`.

Server to client: `OK ...` or `ERROR <code>`. Codes: `BAD_COMMAND`, `LINE_TOO_LONG`,
`NOT_LOGGED_IN`, `ALREADY_LOGGED_IN`, `BAD_USERNAME`, `USERNAME_TAKEN`, `UNKNOWN_SEAT`,
`SEAT_TAKEN`, `LIMIT_REACHED`, `SERVER_ERROR`. The full table is in `docs/` (design document).
