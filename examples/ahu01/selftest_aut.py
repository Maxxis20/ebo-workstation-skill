#!/usr/bin/env python3
"""Self-test of a generated .aut, read back with ebox.parse_aut (independent of the generator's objects).

    python3 selftest_aut.py [AHU01.aut] [io.json]

Checks on every diagram level (program and each HFB):
- every wire starts at a block of that level and an output it has, and every destination is a block of that
  level with an input of that number (no dangling destinations);
- every input of every block is fed exactly once (RI / BI terminals excepted);
- block names at most 20 characters, unique; constants at most 20 characters, unique;
- expressions at most 60 characters and 8 inputs, no letter in both cases;
and, given io.json, that every path in it names a public block of the file.
Exit status 0 = all good.
"""
import json, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "..", "scripts")
sys.path.insert(0, LIB)
from ebox import parse_aut                                     # noqa: E402

CAT = os.path.join(LIB, "..", "reference", "MentaBlocks.xml")
N_IN = {}
for b in ET.parse(CAT).getroot().iter("block"):
    N_IN[b.get("name")] = len(b.findall(".//input"))


def letters(expr):
    return sorted(set(re.findall(r"(?<![A-Za-z0-9_])([A-Za-z])(?![A-Za-z0-9_])", expr)), key=str.lower)


def n_inputs(b):
    if b.typ in ("XPR", "XPB", "XPI"):
        return len(letters(b.par.strip()[1:-1]))
    if b.typ == "HFB":
        return sum(1 for x in b.sub.blocks.values() if x.typ in ("HFAI", "HFDI"))
    if b.typ in ("RI", "BI", "II") or b.typ.startswith("Op"):
        return 0                                                # terminal bound outside / constant operator
    return N_IN[b.typ]


def n_outputs(b):
    if b.typ == "HFB":
        return sum(1 for x in b.sub.blocks.values() if x.typ in ("HFAO", "HFDO"))
    if b.typ in ("HFAO", "HFDO", "RO", "BO", "COMENT", "ALARM"):
        return 1 if b.typ in ("RO", "BO", "ALARM") else 0
    return 1


def main(a):
    aut = a[0] if a else os.path.join(HERE, "AHU01.aut")
    raw = open(aut, "rb").read().decode("latin-1")
    top, consts, _binds, _cyc = parse_aut(raw)
    errs, nwires, nblocks, publics = [], 0, 0, set()
    for path, sc in top.walk():
        where = path or "(top)"
        fed = {}
        for src, out, branches in sc.wires:
            if src not in sc.blocks:
                errs.append(f"{where}: wire from missing block {src}"); continue
            if out >= n_outputs(sc.blocks[src]):
                errs.append(f"{where}: wire from {sc.blocks[src].name} output {out}, which it does not have")
            for _pts, dst, pin in branches:
                nwires += 1
                if dst is None:
                    errs.append(f"{where}: open wire end from {sc.blocks[src].name}"); continue
                if dst not in sc.blocks:
                    errs.append(f"{where}: dangling destination {dst},{pin} from {sc.blocks[src].name}"); continue
                if pin >= n_inputs(sc.blocks[dst]):
                    errs.append(f"{where}: {sc.blocks[dst].typ} {sc.blocks[dst].name} has no input {pin}")
                fed[(dst, pin)] = fed.get((dst, pin), 0) + 1
        names = {}
        for b in sc.blocks.values():
            if b.typ == "COMENT":
                continue
            nblocks += b.typ != "HFB"
            for i in range(n_inputs(b)):
                k = fed.get((b.id, i), 0)
                if k != 1:
                    errs.append(f"{where}: {b.typ} {b.name or '#' + str(b.id)} input {i} fed {k} times")
            if b.name:
                short = b.name.split("\\")[-1]
                if len(short) > 20:
                    errs.append(f"{where}: name {b.name} longer than 20")
                if b.typ not in ("HFAI", "HFDI", "HFAO", "HFDO"):
                    if b.name in names:
                        errs.append(f"{where}: duplicate name {b.name}")
                    names[b.name] = b
                if b.public:
                    publics.add(b.name.replace("\\", "/"))
            if b.typ in ("XPR", "XPB", "XPI"):
                e = b.par.strip()[1:-1]
                L = letters(e)
                if len(e) > 60 or len(L) > 8 or len({c.lower() for c in L}) != len(L):
                    errs.append(f"{where}: expression {e!r} too long or letters mixed")
    cn = [c[0] for c in consts]
    if len(set(cn)) != len(cn):
        errs.append("duplicate constant names")
    errs += [f"constant {n} longer than 20" for n in cn if len(n) > 20]
    io_file = a[1] if len(a) > 1 else os.path.join(HERE, "io.json")
    nio = 0
    if os.path.exists(io_file) and os.path.basename(aut) == "AHU01.aut":
        io = json.load(open(io_file))
        for sec, key in (("inputs", "block"), ("outputs", "signal"), ("setpoints", "path"), ("alarms", "path"),
                         ("states", "path")):
            for e in io[sec]:
                nio += 1
                if e[key] not in publics:
                    errs.append(f"io.json {sec}: {e[key]} is not a public block of the file")
        for e in io["constants"]:
            if e["name"] not in cn:
                errs.append(f"io.json constants: {e['name']} not in [Const]")
    print(f"{os.path.basename(aut)}: {nblocks} blocks, {nwires} wire ends checked, {len(consts)} constants, "
          f"{len(publics)} public names" + (f", {nio} io.json paths checked" if nio else ""))
    for e in errs:
        print("FAIL", e)
    print("OK" if not errs else f"{len(errs)} problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
