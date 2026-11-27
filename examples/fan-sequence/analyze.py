#!/usr/bin/env python3
"""analyze.py <trace.txt> <actions.act> - timeline of one test scenario from the MQTT trace of the program.

Prints, in seconds from the first action: the actions, every change of the step, of the alarm and trip signals,
of the commands and feedbacks, and the step durations D1 ... D5 as the program stored them.
"""
import sys
from datetime import datetime

WATCH = {"Seq/Step": "step", "Seq/Seq_Alarm": "seq alarm", "Seq/AL_Step": "alarm step", "Seq/AL_Req": "alarm req",
         "Seq/Trip": "trip", "Seq/Demand": "demand", "Outputs/Damper_Cmd": "damper cmd", "Outputs/Fan_Cmd": "fan cmd",
         "Sim/Fan_Fdb": "fan fdb"}
DUR = ["Seq/D1", "Seq/D2", "Seq/D3", "Seq/D4", "Seq/D5"]


def load(trace, acts):
    rows = []
    for line in open(trace, encoding="utf-8", errors="replace"):
        parts = line.replace("\x00", "").rstrip("\n").split(" ")
        try:
            t = datetime.fromisoformat(parts[0]).timestamp(); topic = " ".join(parts[1:-1]); v = float(parts[-1])
        except (ValueError, IndexError):
            continue                                                 # a broken line (cut off when the trace stopped)
        key = "/".join(topic.split("/")[-2:])
        rows.append((t, key, v))
    act = []
    for line in open(acts, encoding="utf-8-sig"):
        t, *rest = line.split()
        act.append((float(t.replace(",", ".")), " ".join(rest)))
    return rows, act


def main(trace, acts):
    rows, act = load(trace, acts)
    t0 = act[0][0]
    ev = [(t - t0, "ACTION", a) for t, a in act]
    last, dur = {}, {}
    for t, k, v in rows:
        if k in DUR:
            if v and dur.get(k) != v:
                ev.append((t - t0, "duration", f"{k.split('/')[1]} = {v:.1f} s"))
            dur[k] = v
        if k in WATCH and last.get(k) != v:
            if k in last or v:
                ev.append((t - t0, WATCH[k], f"{v:g}"))
            last[k] = v
    for t, what, s in sorted(ev):
        if t >= -1:
            print(f"{t:7.1f}  {what:<11} {s}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
