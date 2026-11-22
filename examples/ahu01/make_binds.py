#!/usr/bin/env python3
"""make_binds.py [/Server 1] [AHU01] [--no-sim] - every binding of the AHU01 set as one list for `ebox.py bind`.

Written from io.json (controller), sim_io.json (plant simulation) and hmi_binds.json (graphic):
 controller inputs  <- simulation PLANT/<tag>        (with --no-sim: left out, to be bound to field points)
 simulation inputs  <- controller Outputs/<tag>
 graphic bind names <- controller Module/Name, and the test bench ones <- simulation TEST/Name
Output binds.json: [[object path inside the exported folder, binding point, absolute target], ...]."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
server = args[0] if args else "/Server 1"; folder = args[1] if len(args) > 1 else "AHU01"
sim_on = "--no-sim" not in sys.argv
io, sim, hmi = (json.load(open(os.path.join(HERE, f))) for f in ("io.json", "sim_io.json", "hmi_binds.json"))
base = f"{server}/{folder}"; out = []
if sim_on:
    for p in sim["provides"] + sim.get("optional_provides", []):
        if any(i["tag"] == p["tag"] for i in io["inputs"]):
            out.append([f"{folder}/AHU/Inputs", p["tag"], f"{base}/SIM/{p['signal']}"])
    for tag in sim["reads"]:
        out.append([f"{folder}/SIM/IN", tag, f"{base}/AHU/Outputs/{tag}"])
for n in ("Time_Schedule", "Night_Schedule"):                   # weekly schedules made by make_dashboard.py
    out.append([f"{folder}/AHU/Operation", n, f"{base}/Schedules/{n}/Value"])
for name, target in hmi["controller"].items():
    out.append([f"{folder}/Graphic", name, f"{base}/AHU/{target}"])
if sim_on:
    for name, target in hmi.get("bench", {}).items():
        out.append([f"{folder}/Graphic", name, f"{base}/SIM/{target}"])
json.dump(out, open(os.path.join(HERE, "binds.json"), "w"), indent=0)
print(f"binds.json: {len(out)} bindings")
