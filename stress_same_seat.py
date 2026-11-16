"""Many fake clients try to book the SAME seat at the same moment.

Exactly one of them must get OK BOOKED; all the others must get ERROR SEAT_TAKEN.

Run against a server that is already running (good for the demo video and Wireshark):
    python tests/stress_same_seat.py --clients 10 --seat A1

Owner: Mohammad Asaad Alrefai (Testing and Demo Lead)
"""

import argparse
import sys
import threading

from helpers import TestClient


def run_stress(host, port, clients, seat):
    """Return the list of BOOK replies, one per fake client."""
    barrier = threading.Barrier(clients)
    replies = [None] * clients

    def worker(index):
        try:
            client = TestClient(port, host)
            client.login(f"racer{index + 1}")
            barrier.wait()  # everyone sends BOOK at the same moment
            replies[index] = client.request(f"BOOK {seat}")
            client.request("QUIT")
            client.close()
        except Exception as problem:  # record the failure instead of hiding it
            replies[index] = f"EXCEPTION {problem!r}"
            barrier.abort()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(clients)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return replies


def main():
    parser = argparse.ArgumentParser(description="Same-seat booking race test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--clients", type=int, default=10)
    parser.add_argument("--seat", default="A1")
    args = parser.parse_args()

    replies = run_stress(args.host, args.port, args.clients, args.seat)
    for index, reply in enumerate(replies, start=1):
        print(f"racer{index}: {reply}")
    winners = sum(1 for reply in replies if reply == f"OK BOOKED {args.seat.upper()}")
    print(f"\n{winners} client(s) got the seat (expected exactly 1)")
    return 0 if winners == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
