#!/usr/bin/env python3
"""make_dashboard.py - trend logs of the AHU01 measurements and a measurement dashboard, as an EBO import file.

Writes AHU01-objects.xml: folder Trends (one interval log per measurement and control signal, trend charts) and
folder Schedules (the two weekly schedules the controller reads), and
the dashboard Measurements (gauges, live values, charts of the last hour / 24 hours, alarm count, the operator
graphic as a tile). Import below the folder that holds the controller program (default /Server 1/AHU01, program
AHU): Ws-Import '/Server 1/AHU01' ...  The dashboard is shown in WebStation."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from objects import ObjectSet

BASE = sys.argv[1] if len(sys.argv) > 1 else "/Server 1/AHU01"
P = BASE + "/AHU/"
s = ObjectSet(parent=BASE)
tr = s.folder("Trends")

# (log name, signal, seconds)
TEMPS = [("TE00 outdoor", "Inputs/TE00"), ("TE6 intake", "Inputs/TE6"), ("TE3 after recovery", "Inputs/TE3"),
         ("TE4 after heating", "Inputs/TE4"), ("TE5 after cooling", "Inputs/TE5"), ("TE2 supply", "Inputs/TE2"),
         ("TE7 extract", "Inputs/TE7"), ("TE8 exhaust", "Inputs/TE8"), ("TE1 coil return water", "Inputs/TE1")]
PRESS = [("PE1 supply duct", "Inputs/PE1"), ("PE2 extract duct", "Inputs/PE2"), ("PDE4 rotor", "Inputs/PDE4"),
         ("PDE1 filter 2", "Inputs/PDE1"), ("PDE2 extract filter", "Inputs/PDE2"), ("PDE3 filter 1", "Inputs/PDE3")]
CTRL = [("TF01 speed", "Outputs/TF01_Ctrl"), ("PF01 speed", "Outputs/PF01_Ctrl"), ("SC3 rotor", "Outputs/SC3_Ctrl"),
        ("TV1 heating valve", "Outputs/TV1_Ctrl"), ("TV2 cooling valve", "Outputs/TV2_Ctrl")]
logs = {}
for group, sec in ((TEMPS, 60), (PRESS, 60), (CTRL, 60)):
    for name, sig in group:
        logs[name] = s.trend_log(tr, name, P + sig, seconds=sec, size=20000)
g = lambda grp: [logs[n] for n, _ in grp]
s.trend_chart(tr, "Temperatures", g(TEMPS), "AHU01 temperatures")
s.trend_chart(tr, "Pressures", g(PRESS), "AHU01 pressures")
s.trend_chart(tr, "Control signals", g(CTRL), "AHU01 control signals")

# The two weekly schedules the controller reads: its Operation/Time_Schedule and Operation/Night_Schedule bind to
# their Value (make_binds.py). Edit the times here, or in WorkStation by opening the schedule.
c = s.folder("Schedules")
s.schedule(c, "Time_Schedule", {"mon-fri": [("06:30", "18:30")], "sat-sun": [("09:00", "15:00")]}, "Occupied hours")
s.schedule(c, "Night_Schedule", {"mon-fri": [("02:00", "08:00")]}, "Window for night cooling / night heating")

d = s.folder("Dashboard")
w = []
w.append((s.gauge(d, "Supply air", P + "Inputs/TE2", 10, 30, [(16, "#1A73E8"), (21.5, "#D93025")], "Supply air TE2, °C"), 1, 1))
w.append((s.gauge(d, "Supply pressure", P + "Inputs/PE1", 0, 250, [(80, "#1E8E3E")], "Supply duct PE1, Pa"), 1, 1))
w.append((s.gauge(d, "Extract pressure", P + "Inputs/PE2", 0, 250, [(60, "#1E8E3E")], "Extract duct PE2, Pa"), 1, 1))
w.append((s.alarm_count(d, "Alarms", "Active alarms"), 1, 1))
w.append((s.point_values(d, "Air temperatures", [("Outdoor TE00", P + "Inputs/TE00", "temperature"),
                                                ("After recovery TE3", P + "Inputs/TE3", "temperature"),
                                                ("Supply TE2", P + "Inputs/TE2", "temperature"),
                                                ("Extract TE7", P + "Inputs/TE7", "temperature")], "Air temperatures, °C"), 2, 1))
w.append((s.point_values(d, "Control", [("Heat recovery SC3", P + "Outputs/SC3_Ctrl", "none"),
                                       ("Heating valve TV1", P + "Outputs/TV1_Ctrl", "heating"),
                                       ("Cooling valve TV2", P + "Outputs/TV2_Ctrl", "cooling"),
                                       ("Supply fan TF01", P + "Outputs/TF01_Ctrl", "none")], "Control signals, %"), 2, 1))
w.append((s.period_chart(d, "Temperatures 1 h", g(TEMPS)[:8], "last hour", "line", "average", "Temperatures, last hour"), 2, 2))
w.append((s.period_chart(d, "Control 1 h", g(CTRL), "last hour", "line", "average", "Control signals, last hour"), 2, 2))
w.append((s.period_chart(d, "Pressures 24 h", g(PRESS)[:2], "last 24 hours", "line", "average", "Duct pressures, 24 hours"), 2, 2))
w.append((s.period_chart(d, "Filters 7 d", g(PRESS)[3:], "last 7 days", "line", "max", "Filter pressure drops, 7 days"), 2, 2))
w.append((BASE + "/Graphic", 4, 3))
s.dashboard(d, "Measurements", w)
out = s.save(os.path.join(HERE, "AHU01-objects.xml"))
print(f"{out}: {len(logs)} trend logs, 3 charts, {len(w)} dashboard tiles")
