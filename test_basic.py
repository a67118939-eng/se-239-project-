"""Functional tests: every message type, every error, and bad-input handling.

Run from the project folder:  python -m unittest discover -s tests -v

Owner: Mohammad Asaad Alrefai (Testing and Demo Lead)
"""

import time
import unittest

import helpers
from helpers import TestClient


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.server = helpers.start_server()
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.server.shutdown()

    def connect(self, name=None):
        client = TestClient(self.server.port)
        self.clients.append(client)
        if name:
            self.assertEqual(client.login(name), f"OK LOGIN {name}")
        return client


class LoginTests(ServerTestCase):
    def test_login_ok(self):
        self.assertEqual(self.connect().login("sara"), "OK LOGIN sara")

    def test_bad_usernames(self):
        client = self.connect()
        for bad in ("ab", "a" * 16, "sara!", "sa-ra"):
            self.assertEqual(client.request(f"LOGIN {bad}"), "ERROR BAD_USERNAME", bad)

    def test_username_taken_ignoring_case(self):
        self.connect("Sara")
        self.assertEqual(self.connect().login("sara"), "ERROR USERNAME_TAKEN")

    def test_login_twice_on_one_connection(self):
        client = self.connect("sara")
        self.assertEqual(client.login("omar"), "ERROR ALREADY_LOGGED_IN")

    def test_commands_need_login(self):
        client = self.connect()
        for command in ("LIST", "BOOK A1", "MYBOOKING"):
            self.assertEqual(client.request(command), "ERROR NOT_LOGGED_IN", command)

    def test_three_clients_at_once(self):
        clients = [self.connect(name) for name in ("sara", "omar", "lina")]
        for client in clients:
            self.assertTrue(client.request("LIST").startswith("OK SEATS"))


class BookingTests(ServerTestCase):
    def test_list_starts_with_20_free_seats(self):
        reply = self.connect("sara").request("LIST").split()
        self.assertEqual(reply[:2], ["OK", "SEATS"])
        seats = reply[2:]
        self.assertEqual(len(seats), 20)
        self.assertEqual(seats[0], "A1:FREE")
        self.assertEqual(seats[-1], "D5:FREE")
        self.assertTrue(all(seat.endswith(":FREE") for seat in seats))

    def test_book_then_list_shows_booked(self):
        client = self.connect("sara")
        self.assertEqual(client.request("BOOK B3"), "OK BOOKED B3")
        self.assertIn("B3:BOOKED", client.request("LIST").split())

    def test_other_client_sees_the_booking(self):
        self.connect("sara").request("BOOK B3")
        self.assertIn("B3:BOOKED", self.connect("omar").request("LIST").split())

    def test_seat_already_taken(self):
        self.connect("sara").request("BOOK A1")
        self.assertEqual(self.connect("omar").request("BOOK A1"), "ERROR SEAT_TAKEN")

    def test_booking_own_seat_again_is_taken(self):
        client = self.connect("sara")
        client.request("BOOK A1")
        self.assertEqual(client.request("BOOK A1"), "ERROR SEAT_TAKEN")

    def test_unknown_seat(self):
        client = self.connect("sara")
        for seat in ("Z9", "A6", "E1", "A0", "AA"):
            self.assertEqual(client.request(f"BOOK {seat}"), "ERROR UNKNOWN_SEAT", seat)

    def test_lowercase_seat_is_accepted(self):
        self.assertEqual(self.connect("sara").request("BOOK b3"), "OK BOOKED B3")

    def test_limit_of_three_seats(self):
        client = self.connect("sara")
        for seat in ("A1", "A2", "A3"):
            self.assertEqual(client.request(f"BOOK {seat}"), f"OK BOOKED {seat}")
        self.assertEqual(client.request("BOOK A4"), "ERROR LIMIT_REACHED")

    def test_failed_booking_does_not_use_up_the_limit(self):
        other = self.connect("omar")
        other.request("BOOK A1")
        client = self.connect("sara")
        self.assertEqual(client.request("BOOK A1"), "ERROR SEAT_TAKEN")
        for seat in ("A2", "A3", "A4"):
            self.assertEqual(client.request(f"BOOK {seat}"), f"OK BOOKED {seat}")

    def test_mybooking(self):
        client = self.connect("sara")
        self.assertEqual(client.request("MYBOOKING"), "OK MYBOOKING NONE")
        client.request("BOOK C2")
        client.request("BOOK A5")
        self.assertEqual(client.request("MYBOOKING"), "OK MYBOOKING A5 C2")

    def test_bookings_survive_leaving_and_rejoining(self):
        client = self.connect("sara")
        client.request("BOOK D1")
        self.assertEqual(client.request("QUIT"), "OK BYE")
        client.close()
        again = self.reconnect("sara")
        self.assertEqual(again.request("MYBOOKING"), "OK MYBOOKING D1")

    def reconnect(self, name):
        """Log in again; the server may need a moment to notice the old client left."""
        for _ in range(40):
            client = TestClient(self.server.port)
            self.clients.append(client)
            if client.login(name) == f"OK LOGIN {name}":
                return client
            time.sleep(0.05)
        self.fail("could not log in again")


class RobustnessTests(ServerTestCase):
    def test_unknown_command(self):
        client = self.connect("sara")
        for line in ("HELLO", "BOOK", "BOOK A1 A2", "LIST now", "LOGIN", "   ", ""):
            self.assertEqual(client.request(line), "ERROR BAD_COMMAND", repr(line))
        self.assertTrue(client.request("LIST").startswith("OK SEATS"))  # still working

    def test_commands_are_case_insensitive(self):
        client = self.connect("sara")
        self.assertEqual(client.request("book a2"), "OK BOOKED A2")
        self.assertEqual(client.request("mybooking"), "OK MYBOOKING A2")

    def test_windows_line_endings(self):
        client = self.connect()
        client.send_raw(b"LOGIN sara\r\n")
        self.assertEqual(client.read_line(), "OK LOGIN sara")

    def test_binary_garbage(self):
        client = self.connect("sara")
        client.send_raw(b"\xff\xfe\x00\x80\n")
        self.assertEqual(client.read_line(), "ERROR BAD_COMMAND")
        self.assertTrue(client.request("LIST").startswith("OK SEATS"))

    def test_line_too_long(self):
        client = self.connect("sara")
        client.send_raw(b"BOOK " + b"A" * 1000 + b"\n")
        self.assertEqual(client.read_line(), "ERROR LINE_TOO_LONG")
        self.assertTrue(client.request("LIST").startswith("OK SEATS"))  # still in sync

    def test_two_messages_in_one_packet(self):
        client = self.connect()
        client.send_raw(b"LOGIN sara\nLIST\n")
        self.assertEqual(client.read_line(), "OK LOGIN sara")
        self.assertTrue(client.read_line().startswith("OK SEATS"))

    def test_message_split_across_packets(self):
        client = self.connect()
        client.send_raw(b"LOG")
        time.sleep(0.1)
        client.send_raw(b"IN sara\n")
        self.assertEqual(client.read_line(), "OK LOGIN sara")

    def test_quit_closes_connection(self):
        client = self.connect("sara")
        self.assertEqual(client.request("QUIT"), "OK BYE")
        self.assertTrue(client.closed_by_server())

    def test_quit_before_login(self):
        client = self.connect()
        self.assertEqual(client.request("QUIT"), "OK BYE")

    def test_sudden_disconnect_frees_the_username_and_server_survives(self):
        victim = self.connect("sara")
        victim.request("BOOK A1")
        victim.close()  # no QUIT: the connection just drops
        for _ in range(40):  # the server notices within a moment
            client = TestClient(self.server.port)
            self.clients.append(client)
            if client.login("sara") == "OK LOGIN sara":
                break
            time.sleep(0.05)
        else:
            self.fail("username was never freed after a sudden disconnect")
        self.assertEqual(client.request("MYBOOKING"), "OK MYBOOKING A1")
        self.assertEqual(self.connect("omar").request("BOOK A2"), "OK BOOKED A2")

    def test_connect_and_drop_without_sending(self):
        TestClient(self.server.port).close()
        self.assertEqual(self.connect().login("sara"), "OK LOGIN sara")


if __name__ == "__main__":
    unittest.main()
