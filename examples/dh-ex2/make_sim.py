#!/usr/bin/env python3
"""DH-ex2-SIM plant model: Function Block program for /Server 1/DH-ex2-SIM (module PLANT).

Operator values: TOUT (outdoor temperature, degC), DHW_TAP (hot water tapping, l/min), P1_TRIP / P2_TRIP (1 = the pump's
motor protection has tripped: the pump stops and the controller gets the fault).
Hot water exchanger: TE1 -> 8 + 82 * v / (v + 3.66 * (1 + tap)), v = valve %, cold water 8, primary 90 degC; lag 8 s.
Heating exchanger:   TE2A -> 25 + 70 * v / (v + 60), return 25, primary 95 degC; lag 30 s.
P1 is the circulation pump: the hot water exchanger works without it (tapping flow). P2 stopped: TE2A settles at 20 degC (room). All temperatures stay between 8 and 90 degC.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from aut import Program


def build():
    p = Program("DH-ex2-SIM")
    m = "PLANT"

    def x(typ, name, expr, ins, public=False):
        b = p.block(typ, name, [expr], public=public, module=m)
        for letter, src in ins.items():
            p.wire(src, b, letter)
        return b

    def chain(typ, name, params, src, public=True):
        b = p.block(typ, name, params, public=public, module=m); p.wire(src, b); return b

    ri = {n: p.block("RI", n, [0], module=m) for n in ("TV1_IN", "P1_IN", "TV2_IN", "P2_IN")}
    tout = p.block("PVR", "TOUT", [-5], public=True, module=m)
    tap = p.block("PVR", "DHW_TAP", [6], public=True, module=m)
    chain("LIMIT", "TE2B", [-50, 50], tout)                                   # outdoor sensor
    tap_l = chain("LIMIT", "TAP_FLOW", [0, 30], tap, public=False)
    tv1 = chain("LIMIT", "TV1_POS", [0, 100], ri["TV1_IN"])
    p1 = x("XPB", "P1_ON", "A>0.5&B<0.5", {"A": ri["P1_IN"], "B": p.block("PVR", "P1_TRIP", [0], public=True, module=m)}, True)
    te1s = x("XPR", "TE1_STATIC", "8+82*A/(A+3.66*(1+B))", {"A": tv1, "B": tap_l})
    chain("FILT", "TE1", [8], te1s)
    tv2 = chain("LIMIT", "TV2_POS", [0, 100], ri["TV2_IN"])
    p2 = x("XPB", "P2_ON", "A>0.5&B<0.5", {"A": ri["P2_IN"], "B": p.block("PVR", "P2_TRIP", [0], public=True, module=m)}, True)
    te2s = x("XPR", "TE2A_STATIC", "p?25+70*A/(A+60):20", {"A": tv2, "p": p2})
    chain("FILT", "TE2A", [30], te2s)
    return p


if __name__ == "__main__":
    p = build()
    p.save(os.path.join(HERE, "DH-ex2-SIM.aut"))
    bad = p.overlaps()
    print(p.stats(), "overlaps:", bad)
    sys.exit(1 if bad else 0)
