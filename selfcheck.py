"""Self-check: runs the project's required features and prints PASS or FAIL for each.

Usage (from the project folder):  python tests/selfcheck.py
It starts its own temporary server, so you do not need to start one.

Owner: Mohammad Asaad Alrefai (Testing and Demo Lead)
"""

import os
import subprocess
import sys
import time

import helpers
from helpers import TestClient
from stress_same_seat import run_stress

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
results = []


def check(name, test):
    try:
        outcome = test()
        ok, note = (outcome if isinstance(outcome, tuple) else (bool(outcome), ""))
    except Exception as problem:
        ok, note = False, f"error: {problem!r}"
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({note})" if note else ""))


def new_server():
    return helpers.start_server()


def three_clients():
    server = new_server()
    clients = [TestClient(server.port) for _ in range(3)]
    try:
        replies = [c.login(n) for c, n in zip(clients, ("sara", "omar", "lina"))]
        listing = [c.request("LIST") for c in clients]
        return (all(r.startswith("OK LOGIN") for r in replies)
                and all(r.startswith("OK SEATS") for r in listing))
    finally:
        [c.close() for c in clients]
        server.shutdown()


def login_required():
    server = new_server()
    client = TestClient(server.port)
    try:
        before = client.request("BOOK A1")
        after = client.login("sara")
        return before == "ERROR NOT_LOGGED_IN" and after == "OK LOGIN sara"
    finally:
        client.close()
        server.shutdown()


def booking_between_clients():
    server = new_server()
    a, b = TestClient(server.port), TestClient(server.port)
    try:
        a.login("sara")
        b.login("omar")
        first, second = a.request("BOOK B3"), b.request("BOOK B3")
        replies = run_stress("127.0.0.1", server.port, 10, "D4")
        winners = replies.count("OK BOOKED D4")
        return (first == "OK BOOKED B3" and second == "ERROR SEAT_TAKEN" and winners == 1,
                f"10 simultaneous clients: {winners} winner")
    finally:
        a.close()
        b.close()
        server.shutdown()


def status_command():
    server = new_server()
    a, b = TestClient(server.port), TestClient(server.port)
    try:
        a.login("sara")
        b.login("omar")
        a.request("BOOK C2")
        seats = b.request("LIST").split()
        return len(seats) == 22 and "C2:BOOKED" in seats and "C1:FREE" in seats
    finally:
        a.close()
        b.close()
        server.shutdown()


def clean_disconnect():
    server = new_server()
    a, b = TestClient(server.port), TestClient(server.port)
    try:
        a.login("sara")
        b.login("omar")
        bye = a.request("QUIT")
        return (bye == "OK BYE" and a.closed_by_server()
                and b.request("LIST").startswith("OK SEATS"))
    finally:
        a.close()
        b.close()
        server.shutdown()


def survives_bad_input():
    server = new_server()
    a, b = TestClient(server.port), TestClient(server.port)
    try:
        a.login("sara")
        b.login("omar")
        a.send_raw(b"\xff\xfe garbage\n")
        garbage = a.read_line()
        unknown = a.request("HELLO")
        a.send_raw(b"BOOK " + b"A" * 1000 + b"\n")
        too_long = a.read_line()
        a.close()  # sudden disconnect, no QUIT
        time.sleep(0.2)
        return (garbage == "ERROR BAD_COMMAND" and unknown == "ERROR BAD_COMMAND"
                and too_long == "ERROR LINE_TOO_LONG"
                and b.request("BOOK A1") == "OK BOOKED A1")
    finally:
        b.close()
        server.shutdown()


def commits_from_everyone():
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=PROJECT,
                             capture_output=True, text=True).stdout.strip()
        if os.path.normcase(os.path.abspath(top)) != os.path.normcase(PROJECT):
            return None
        names = subprocess.run(["git", "log", "--format=%an"], cwd=PROJECT,
                               capture_output=True, text=True).stdout.split("\n")
    except OSError:
        return None
    authors = {name for name in names if name}
    return len(authors) >= 5, f"{len(authors)} different authors in the Git history"


def main():
    print("\nRequired features (automatic checks):")
    check("1. Server accepts 3 clients at the same time", three_clients)
    check("2. Login is required, and a username logs in", login_required)
    check("3. Main feature: booking works between clients, one winner per seat",
          booking_between_clients)
    check("4. LIST shows the current state correctly", status_command)
    check("5. A client can disconnect cleanly; others keep working", clean_disconnect)
    check("6. Server survives bad input and a sudden disconnect", survives_bad_input)
    git = commits_from_everyone()
    if git is None:
        print("  [SKIP] 7. Commits from all 5 members (run this inside your cloned repository)")
    else:
        check("7. Commits from all 5 members", lambda: git)
    print(f"\n{sum(results)} of {len(results)} automatic checks passed.")
    print("Still to check by hand: each member can explain their code, the Wireshark")
    print("capture, the test checklist, the report, and the recorded video.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
