"""Concurrency tests: the booking race. No seat may ever go to two clients.

Run from the project folder:  python -m unittest discover -s tests -v

Owner: Mohammad Asaad Alrefai (Testing and Demo Lead)
"""

import threading
import unittest

import helpers
import config
from helpers import TestClient
from stress_same_seat import run_stress


class ConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.server = helpers.start_server()

    def tearDown(self):
        self.server.shutdown()

    def test_same_seat_only_one_winner(self):
        for round_number in range(10):  # repeat: a race can hide in a single run
            self.server.system = type(self.server.system)()  # fresh seats each round
            replies = run_stress("127.0.0.1", self.server.port, 12, "A1")
            winners = [r for r in replies if r == "OK BOOKED A1"]
            losers = [r for r in replies if r == "ERROR SEAT_TAKEN"]
            self.assertEqual(len(winners), 1, f"round {round_number}: {replies}")
            self.assertEqual(len(losers), 11, f"round {round_number}: {replies}")

    def test_everyone_grabs_everything(self):
        """8 clients all try to book all 20 seats at once. No seat may be given twice."""
        names = [f"fan{n}" for n in range(8)]
        barrier = threading.Barrier(len(names))
        won = {name: [] for name in names}
        errors = []

        def worker(name):
            try:
                client = TestClient(self.server.port)
                client.login(name)
                barrier.wait()
                for seat in config.ALL_SEATS:
                    if client.request(f"BOOK {seat}").startswith("OK BOOKED"):
                        won[name].append(seat)
                client.request("QUIT")
                client.close()
            except Exception as problem:
                errors.append(repr(problem))
                barrier.abort()

        threads = [threading.Thread(target=worker, args=(name,)) for name in names]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        all_won = [seat for seats in won.values() for seat in seats]
        self.assertEqual(len(all_won), len(set(all_won)), "a seat was given to two clients")
        for name, seats in won.items():
            self.assertLessEqual(len(seats), 3, f"{name} got more than 3 seats")
        # Every seat that was won shows as BOOKED, and nothing else does.
        checker = TestClient(self.server.port)
        checker.login("checker")
        booked = [s.split(":")[0] for s in checker.request("LIST").split()[2:]
                  if s.endswith(":BOOKED")]
        checker.close()
        self.assertEqual(sorted(booked), sorted(all_won))
        self.assertEqual(len(all_won), 20)  # 8 clients x 3 seats is enough to fill all 20


if __name__ == "__main__":
    unittest.main()
