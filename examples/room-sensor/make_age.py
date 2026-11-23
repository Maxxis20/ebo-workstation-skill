#!/usr/bin/env python3
"""make_age.py - SensorAge.aut: how long ago a polled sensor last gave a new value.

A device that is polled (no COV, no time stamp of its own) shows the same numbers until its next reading. This
small program watches up to three values and counts the seconds since any of them changed:
    inputs  V1, V2, V3 (bind them to the sensor's values)
    outputs Age_Min (minutes since the last change), Stale (1 when older than STALE_MIN minutes)
It is "last change", not "last report": a reading that repeats all three numbers exactly does not reset it.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from aut import Program

STALE_MIN = 30
p = Program("SensorAge", cycle_ms=1000)
ins = [p.block("RI", f"V{i}", desc=f"Watched value {i}") for i in (1, 2, 3)]
prev = []
for i, b in enumerate(ins, 1):
    d = p.block("DELR", f"V{i}_Prev", [0]); p.wire(b, d); prev.append(d)
chg = p.block("XPB", "Changed", ["(ABS(A-B)>0.0005)|(ABS(C-D)>0.0005)|(ABS(E-F)>0.0005)"],
              desc="A watched value differs from the cycle before")
for letter, src in zip("ABCDEF", (ins[0], prev[0], ins[1], prev[1], ins[2], prev[2])):
    p.wire(src, chg, letter)
tc = p.block("TCYC", "Cycle_s")
age = p.block("XPR", "Age_s", ["a?0:B+C"], unit="s", desc="Seconds since the last change")
age_prev = p.block("DELR", "Age_Prev", [0])
p.wire(chg, age, "a"); p.wire(age_prev, age, "B"); p.wire(tc, age, "C"); p.wire(age, age_prev)
mins = p.block("XPR", "Age_Min", ["A/60"], public=True, desc="Minutes since the last change"); p.wire(age, mins, "A")
stale = p.block("XPB", "Stale", [f"A>{STALE_MIN}"], public=True, desc=f"No change for more than {STALE_MIN} minutes")
p.wire(mins, stale, "A")
p.check(); p.layout(); p.save(os.path.join(HERE, "SensorAge.aut"))
print("SensorAge.aut:", p.stats())
