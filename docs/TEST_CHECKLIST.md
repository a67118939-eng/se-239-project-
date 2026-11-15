# Test checklist

Fill in the last two columns by hand while testing with real terminals (server + 3 or more
clients). The automated tests (`python -m unittest discover -s tests -v`) cover the same
cases; this table is the written record for the report.

| # | What we tried | What we expected | What happened | Pass/Fail |
|---|---|---|---|---|
| 1 | 3 clients connect and log in with different names | All three get `OK LOGIN` | | |
| 2 | A second client logs in with a name already online (also with different upper/lower case) | `ERROR USERNAME_TAKEN` | | |
| 3 | Username `ab` or `sara!` | `ERROR BAD_USERNAME` | | |
| 4 | `LIST` before logging in | `ERROR NOT_LOGGED_IN` | | |
| 5 | `LIST` after login | 20 seats, free ones and booked ones shown correctly | | |
| 6 | Client 1 books B3 | `OK BOOKED B3` | | |
| 7 | Client 2 then books B3 | `ERROR SEAT_TAKEN` | | |
| 8 | Client 2 runs `LIST` | B3 shows as booked | | |
| 9 | Book `Z9` | `ERROR UNKNOWN_SEAT` | | |
| 10 | Book a 4th seat for one user | `ERROR LIMIT_REACHED` | | |
| 11 | `MYBOOKING` with and without bookings | Seat list, or `NONE` | | |
| 12 | 10 fake clients book A1 at the same moment (`tests/stress_same_seat.py`) | Exactly one `OK BOOKED A1`, nine `SEAT_TAKEN` | | |
| 13 | Send a nonsense command (`raw HELLO`) | `ERROR BAD_COMMAND`, server keeps running | | |
| 14 | Close a client window without typing `quit` | Server keeps running, other clients unaffected, name freed | | |
| 15 | `quit` | `OK BYE`, client exits, server keeps running | | |
| 16 | Log back in with the same name after leaving | Earlier bookings are still there | | |
| 17 | Stop the server with Ctrl+C | Server stops cleanly, no crash message | | |
