# Test results (2026-11-27, EBO 7.1.1.132 Enterprise Server only, on a Windows machine)

What it ran on: one Enterprise Server with WorkStation, the Mosquitto broker and the spot price bridge (`spotd.py`,
fake source, Python 3.12 with `tzdata`) on the same Windows machine; no controller, no I/O (README, "What it ran
on"). WorkStation logged on as a user of a group with Automatic logoff = Never, so it stays logged on while a test
plays (the tests do not touch WorkStation for minutes at a time).

Each step writes a fake price file with its own clock (`make_fake.py`, `fake/*.json`); the bridge reads it within
10 s and publishes `spot/FI/points`, which the client `Prices` writes into the 219 values of folder `Spot`.
Settings go in through the Test client's subscription. The program's signals come out through data groups and
`analyze.py` makes `test-out/<test>-timeline.txt` (trace times are whole seconds). Screenshots
`test-out/<test>-<n>-<what>.png` are cropped to the graphic, found on the screen by its header (WorkStation scales
it to the window); `<test>-al<n>-*.png` show the Alarm View filtered to the example. Every test starts with price
control on, mode "N cheapest hours", N 6, block 3 h, block limit 20 c/kWh, force limit 0, normal demand on,
hourly prices, c/kWh. Times below are seconds from the start of the test.

## t1 normal day, N cheapest hours - pass

| Clock (fake) | Price | Rank | Reason (expected) | Load |
|---|---|---|---|---|
| 03:30 | 2.0 | 1 | 1 chosen hour | on |
| 08:30 | 26.5 | 23 | 3 above block limit | off |
| 12:30 | 12.0 | 13 | 2 not chosen | off |
| 12:30, price control off | | | 0 price control off | on (normal demand) |

## t2 negative prices - pass

13:30, price -2.1 c/kWh (rank 1 but also at or below the force limit 0): reason 4 (forced), load on. Bars below
zero in blue (`t2-1-forced`).

## t3 cheapest 3 h in a row: plan, count down, plan again when tomorrow arrives - pass

12:30, 12 hours known (tomorrow not out): mode 1 set at 15 s, planned at once: starts in 3 h (15:00-18:00, prices
3.0 / 3.2 / 3.1). 13:30: the hour changed, starts in 2 h (counted down, not planned again). 14:05 with tomorrow's
prices (34 hours known): planned again while still waiting: starts in 12 h (tomorrow 02:00-05:00, 1.0 / 0.9 / 1.1).
`t3-3-replanned`: those three bars green.

## t4 held block - pass

14:30: planned, starts in 1 h (15:00-18:00 at 2.0 / 2.1 / 2.2; tomorrow 9.0 flat). 15:30: running, load on.
16:30: tomorrow's night now much cheaper (`blk3` from the bridge = 10 h), but the block keeps running: 2 h left
(`t4-3-still-held`). 17:30: 1 h left. 18:30: block over, load off, planned again: starts in 8 h (tomorrow 02:00).

## t5 source dead (valid 0) - pass

12:30 normal: reason 2. Source dead at 22 s (fake `dead`, `max_age_s` 20): `valid` 0 at 41 s, reason 5, load
follows normal demand (on); alarm `Price_Invalid` active with its text (`t5-al1-active`). Source back at 88 s:
valid 1 at 91 s, reason 2, alarm returned to normal (`t5-al2-reset`).

## t6 bridge stopped - pass

Bridge process stopped at 22 s: the beat stands still, `Stale` and reason 5 at 81 s (60 s after the last beat),
load on normal demand; alarm `Bridge_Stopped` active (`t6-al1-active`). Bridge started at 122 s: stale 0, reason 2
in the same trace second; alarm back to normal (`t6-al2-reset`).

## t7 15 minute prices, EUR/MWh - pass

12:20, the hour 12:00-13:00 averages 13.75 c/kWh but its second quarter costs 25.0. Hourly: reason 2 (not chosen).
15 min at 27 s: reason 3 (above block limit, the quarter's price), graph shows 36 quarters = 9 h with hh:mm labels
(`t7-2-quarters`). EUR/MWh: the price now 250.00 EUR/MWh, today's values, the N-th price and the axis x10; the
settings stay in c/kWh (`t7-3-eur-mwh`). Back to hourly: reason 2.

## Alarm objects

`Alarms/Price_Invalid` and `Alarms/Bridge_Stopped` (priority 2) go active with their texts and return to normal
in the Alarm View; not acknowledged in the tests, which the header lamps show as a ring ("gone, not
acknowledged"). Their Count column also counts earlier runs on the same server.

## Not done / limits

- Live prices on this machine: the EBO machine has no internet (by design: the bridge stays outside, MQTT between).
  The live bridge was run as a container beside a containerised Enterprise Server (`bridge-container/`): 96
  quarters for FI fetched, `spot/FI/now` valid on its local broker. Connecting that broker to this server was not
  done (it listens on loopback only).
- N cheapest quarters / cheapest N quarters in a row: the choice of hours stays hourly (the bridge ranks hours;
  ranking 96 values in a Function Block program is not practical). 15 min applies to the limits and the graph.
- The load is a program output only; "normal operation" is a server value standing in for a thermostat.
