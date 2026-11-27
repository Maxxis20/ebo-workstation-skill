#!/usr/bin/env python3
"""analyze.py <trace.txt> <actions.act> - timeline of one spot price test from the MQTT trace of the program.

Prints, in seconds from the first action: the actions and every change of the watched signals."""
import sys
from datetime import datetime

WATCH = {"Inputs/Valid": "valid", "Inputs/Hour": "hour", "Inputs/Price": "price", "Inputs/Rank": "rank",
         "Inputs/Known": "known", "Ctl/Reason": "REASON", "Ctl/Load_Cmd": "LOAD", "Ctl/No_Price": "no price",
         "Ctl/Stale": "stale", "Ctl/Chosen": "chosen", "Ctl/Block_Mode": "block mode", "Plan/Planned": "planned",
         "Plan/Plan_Wait": "plan wait", "Plan/Plan_Left": "plan left", "Plan/In_Block": "in block",
         "Plan/Replan": "replan", "Block/Best_In": "best in", "Hmi/N_Price": "N-th price"}
REASON = {0: "price control off", 1: "chosen hour", 2: "not chosen", 3: "above block limit",
          4: "at/below force limit", 5: "no price data"}


def load(trace, acts):
    rows = []
    for line in open(trace, encoding="utf-8", errors="replace"):
        parts = line.replace("\x00", "").rstrip("\n").split(" ")
        try:
            t = datetime.fromisoformat(parts[0]).timestamp(); v = float(parts[-1])
        except (ValueError, IndexError):
            continue                                     # JSON payloads and broken lines
        rows.append((t, "/".join(" ".join(parts[1:-1]).split("/")[-2:]), v))
    act = []
    for line in open(acts, encoding="utf-8-sig"):
        t, *rest = line.split()
        act.append((float(t.replace(",", ".")), " ".join(rest)))
    return rows, act


def main(trace, acts):
    rows, act = load(trace, acts)
    t0 = act[0][0]
    ev = [(t - t0, "ACTION", s) for t, s in act]
    last = {}
    for t, k, v in rows:
        if k in WATCH and last.get(k) != v:
            s = f"{v:g}" + (f"  {REASON.get(int(v), '')}" if k == "Ctl/Reason" else "")
            ev.append((t - t0, WATCH[k], s))
            last[k] = v
    for t, what, s in sorted(ev, key=lambda e: e[0]):
        if t >= -1:
            print(f"{t:7.1f}  {what:<11} {s}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
