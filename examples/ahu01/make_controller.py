#!/usr/bin/env python3
"""make_controller.py - the AHU01 I/O for a SpaceLogic MP-C-36A, as files for EBO.

The controller object itself is made in WorkStation (BACnet Interface > IP Network > New > SpaceLogic Series >
MP-C-36A; it can be made offline, without the hardware), and the program is loaded into its Application with
    Fb-Load '<controller>/Application' 'AHU' AHU01.aut 'SpaceLogic Function Block Program'
This script writes
  AHU01-MPC-points.xml   I/O points with their terminals, and the values that arrive over the network, to import
                         below <controller>/Application. Output points take their value from the program's output blocks
                         Outputs/<tag>_OUT (an I/O point accepts only an output block as its source).
  mpc_binds.json         the program's input bindings (Inputs/<tag> <- point Value) for `ebox.py bind` on an export
                         of the program.
  MPC_IO.md              the terminal list for the panel builder.

Terminals of an MP-C-36A: Ub 1-20 universal inputs, Uc 1-8 universal inputs / outputs, DO 1-8 relay outputs.
39 physical points do not fit on 36 terminals, so the points that a site normally has on the network anyway come
in as BACnet values: outdoor temperature TE00, the three room temperatures TE10_1..3 and the remote reset.
With an IP-IO-DI10 module beside the controller they can be wired instead."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from objects import ObjectSet

args = [a for a in sys.argv[1:] if not a.startswith("--")]
CTRL = args[0] if args else "/Server 1/BACnet/IP Network/AHU01-MPC"
# An output point takes its value only from an output block of the program, and a private block is addressed by
# its GUID, which the editor gives at the save. So: load the program into the controller, export it (Special), and
# pass that file here as the second argument; without it the output points are written unbound.
GUID = {}
if len(args) > 1:
    import re
    from ebox import Export
    for _who, par, raw in Export(args[1]).files():
        if par == "AutFile":
            for m in re.finditer(r'"Outputs\\(\w+_OUT)"[^\n]*?\'([0-9A-Fa-f-]{36})\' = [RB]O', raw.decode("utf-8", "replace")):
                GUID[m.group(1)] = m.group(2).upper()
APP = CTRL + "/Application"; IO = CTRL + "/IO Resources/Onboard IO/"
io = json.load(open(os.path.join(HERE, "io.json")))
NETWORK = {"TE00": ("AV", -5.0), "TE10_1": ("AV", 21.0), "TE10_2": ("AV", 21.0), "TE10_3": ("AV", 21.0), "Reset_DI": ("BV", 0)}
PT = "bacnet.mpx.point."
s = ObjectSet(parent=APP)
ub = iter(f"Ub {i}" for i in range(1, 21)); uc_out = iter(f"Uc {i}" for i in range(1, 9)); do = iter(f"DO {i}" for i in range(1, 9))
rows, binds = [], []
def rng(i):
    lo, hi = (i.get("range") or "0 ... 100").split("...")
    return float(lo), float(hi)
def out_ref(o):
    g = GUID.get(o["block"].split("/")[1])
    return {"Value": f"{APP}/AHU/Outputs/{g}"} if g else {}
ins = [i for i in io["inputs"] if i["kind"] in ("AI", "DI") and i["tag"] not in NETWORK]
outs = io["outputs"]
ao = [o for o in outs if o["kind"] == "AO"]
for o in ao:                                                # analog outputs first: they need the Uc terminals
    t = next(uc_out)
    s.obj(None, PT + "VoltageOutput", o["tag"], {"ElecBottomOfScale": 0, "ElecTopOfScale": 10, "EngBottomOfScale": 0,
                                                "EngTopOfScale": 100, "DESCR": o["tag"] + " 0-10 V = 0-100 %"},
          {"Terminal": IO + t + "/", **out_ref(o)})
    rows.append((t, o["tag"], "AO 0-10 V", "0 ... 100 %"))
for o in outs:
    if o["kind"] == "DO":
        t = next(do)
        s.obj(None, PT + "DigitalOutput", o["tag"], {"DESCR": o["tag"]},
              {"Terminal": IO + t + "/", **out_ref(o)})
        rows.append((t, o["tag"], "DO relay", ""))
free_uc = list(uc_out)
terms = [f"Ub {i}" for i in range(1, 21)] + free_uc
for i, t in zip(ins, terms):
    if i["kind"] == "DI":
        s.obj(None, PT + "DigitalInput", i["tag"], {"DESCR": i["tag"]}, {"Terminal": IO + t + "/"})
        rows.append((t, i["tag"], "DI contact", ""))
    elif i.get("unit") == "°C":
        s.obj(None, PT + "TemperatureInput", i["tag"], {"DESCR": i["tag"]}, {"Terminal": IO + t + "/"})
        rows.append((t, i["tag"], "temperature sensor", i.get("range", "")))
    else:
        lo, hi = rng(i)
        s.obj(None, PT + "VoltageInput", i["tag"], {"ElecBottomOfScale": 0, "ElecTopOfScale": 10, "EngBottomOfScale": lo,
                                                   "EngTopOfScale": hi, "DESCR": f"{i['tag']} 0-10 V = {lo:g} ... {hi:g} {i.get('unit','')}"},
              {"Terminal": IO + t + "/"})
        rows.append((t, i["tag"], "AI 0-10 V", f"{lo:g} ... {hi:g} {i.get('unit','')}"))
    binds.append(["AHU/" + i["block"].split("/")[0], i["tag"], f"{APP}/{i['tag']}/Value"])
if len(ins) > len(terms):
    raise SystemExit(f"{len(ins)} inputs for {len(terms)} input terminals")
for tag, (kind, val) in NETWORK.items():
    s.value(None, tag, val, kind); rows.append(("network", tag, "BACnet value " + kind, "written by the server or another controller"))
    mod = next(i["block"].split("/")[0] for i in io["inputs"] if i["tag"] == tag)
    binds.append(["AHU/" + mod, tag, f"{APP}/{tag}/Value"])
s.save(os.path.join(HERE, "AHU01-MPC-points.xml"))
json.dump(binds, open(os.path.join(HERE, "mpc_binds.json"), "w"), indent=0)
with open(os.path.join(HERE, "MPC_IO.md"), "w") as f:
    f.write("# AHU01 on a SpaceLogic MP-C-36A: terminals\n\n| Terminal | Point | Kind | Range |\n|---|---|---|---|\n")
    f.write("".join(f"| {a} | {b} | {c} | {d} |\n" for a, b, c, d in rows))
    f.write("\nSoft inputs of the program (schedules, mode selectors, heat supply alarms) are not wired: bind them to\n"
            "schedule objects, values or other controllers on the site.\n")
print(f"output points bound to the program: {len(GUID)} of {len(outs)}" + ("" if GUID else "  (pass an export of the loaded program to bind them)"))
print(f"{len(rows)} points ({len(ins)} wired inputs, {len(outs)} outputs, {len(NETWORK)} network values), {len(binds)} program input bindings")
