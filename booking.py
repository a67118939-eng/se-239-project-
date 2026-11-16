"""Seat table and booking rules.

All shared data (seats, bookings, online users) lives in one BookingSystem object
and is only read or changed while holding one threading.Lock. That lock is what
guarantees a seat is never given to two clients, even if their BOOK requests
arrive at almost the same moment.

Owner: Abdulaziz Al Thunyan (Booking Logic Lead)
"""

import threading

import config


class BookingError(Exception):
    """A request that cannot be done. `code` is the error code sent to the client."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class BookingSystem:
    def __init__(self):
        self._lock = threading.Lock()
        self._order = {seat: index for index, seat in enumerate(config.ALL_SEATS)}
        self._seats = {seat: None for seat in config.ALL_SEATS}  # seat -> owner key or None
        self._bookings = {}   # owner key -> list of seats; kept after the user leaves
        self._online = set()  # owner keys of users currently logged in

    @staticmethod
    def _key(username):
        # Usernames are compared ignoring upper/lower case ("Sara" and "sara" are one user).
        return username.lower()

    def login(self, username):
        """Mark a user online. Raises BookingError(USERNAME_TAKEN) if the name is in use."""
        key = self._key(username)
        with self._lock:
            if key in self._online:
                raise BookingError(config.USERNAME_TAKEN)
            self._online.add(key)
            self._bookings.setdefault(key, [])

    def logout(self, username):
        """Mark a user offline. Their bookings stay. Safe to call more than once."""
        with self._lock:
            self._online.discard(self._key(username))

    def book_seat(self, username, seat):
        """Book one seat for a user. The check and the assignment happen under one lock."""
        key = self._key(username)
        with self._lock:
            if seat not in self._seats:
                raise BookingError(config.UNKNOWN_SEAT)
            if self._seats[seat] is not None:
                raise BookingError(config.SEAT_TAKEN)
            if len(self._bookings[key]) >= config.MAX_SEATS_PER_USER:
                raise BookingError(config.LIMIT_REACHED)
            self._seats[seat] = key
            self._bookings[key].append(seat)

    def list_seats(self):
        """Return [(seat, 'FREE' or 'BOOKED'), ...] for all seats, in seat order."""
        with self._lock:
            return [(seat, "FREE" if owner is None else "BOOKED")
                    for seat, owner in self._seats.items()]

    def my_bookings(self, username):
        """Return the seats this user has booked, in seat order."""
        with self._lock:
            seats = list(self._bookings.get(self._key(username), []))
        return sorted(seats, key=self._order.get)
