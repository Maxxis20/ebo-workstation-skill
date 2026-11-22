#!/usr/bin/env python3
"""DH-ex2 controller: Function Block program for /Server 1/DH-ex2 (modules OUTDOOR, TC1_DHW, TC2_HEAT, ALARM)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from aut import Program


def build():
    p = Program("DH-ex2")
    # set values that are block parameters: program constants (properties of the program object)
    for n, v in [("TOUT_FILT_T", 900), ("DHW_ALM_DLY", 300), ("SUM_DLY", 3600), ("CRV_N20", 58), ("CRV_0", 41),
                 ("CRV_P20", 20), ("TS_MIN", 18), ("TS_MAX", 70), ("HEAT_ALM_DLY", 600)]:
        p.const(n, v)

    def sv(m, name, v):                         # public set value
        return p.block("PVR", name, [v], public=True, module=m)

    def k(m, name, v):                          # private fixed constant
        return p.block("PVR", name, [v], module=m)

    def x(m, typ, name, expr, ins, public=False):
        b = p.block(typ, name, [expr], public=public, module=m)
        for letter, src in ins.items():
            p.wire(src, b, letter)
        return b

    def pid(m, name, mv, sp, en, pband, ti):
        mode = x(m, "XPI", name + "_MODE", "e?1:3", {"e": en})          # 1 normal, 3 forced to UMin = 0 %
        g = x(m, "XPR", name + "_G", "100/A", {"A": pband})             # gain = 100 / proportional band
        c = p.block("PIDA", name, [1, 0, 100, 60], public=True, module=m)
        for pin, src in [("MV", mv), ("SP", sp), ("Mode", mode), ("G", g), ("Ti", ti),
                         ("Td", k(m, name + "_TD", 0)), ("DZ", k(m, name + "_DZ", 0.5))]:
            p.wire(src, c, pin)
        p.wire(c, c, "TSg")                                             # own output back to the tracking signal
        return c

    # 1 OUTDOOR
    m = "OUTDOOR"
    te2b_in = p.block("RI", "TE2B_IN", [0], module=m)
    te2b = x(m, "XPR", "TE2B", "A", {"A": te2b_in}, True)
    f2b = x(m, "XPB", "TE2B_FAULT", "A<-45|A>50", {"A": te2b}, True)
    sel = x(m, "XPR", "TE2B_SEL", "f?B:A", {"A": te2b, "B": sv(m, "TOUT_FALLBACK", 0), "f": f2b})
    te2b_f = p.block("FILT", "TE2B_F", ["TOUT_FILT_T"], public=True, module=m); p.wire(sel, te2b_f)

    # 2 TC1_DHW
    m = "TC1_DHW"
    te1 = x(m, "XPR", "TE1", "A", {"A": p.block("RI", "TE1_IN", [0], module=m)}, True)
    f1 = x(m, "XPB", "TE1_FAULT", "A<-20|A>120", {"A": te1}, True)
    p1 = x(m, "XPB", "P1_RUN", "A>0.5", {"A": sv(m, "DHW_ENABLE", 1)}, True)
    pf1 = x(m, "XPB", "P1_FAULT", "A>0.5", {"A": p.block("RI", "P1_FLT_IN", [0], module=m)}, True)   # motor protection of P1 (HS)
    x(m, "XPI", "P1_ST", "f?2:(r?1:0)", {"f": pf1, "r": p1}, True)        # 0 stopped, 1 running, 2 fault: for displays
    en1 = x(m, "XPB", "DHW_CTRL_EN", "p&!f", {"p": p1, "f": f1})      # a P1 fault only alarms: tapping still flows through the exchanger
    tv1 = pid(m, "TV1", te1, sv(m, "DHW_SP", 58), en1, sv(m, "DHW_PID_P", 60), sv(m, "DHW_PID_I", 15))
    a1 = x(m, "XPB", "DHW_ALM_RAW", "e&(A>B|A<C)", {"A": te1, "B": sv(m, "DHW_HI_LIM", 65), "C": sv(m, "DHW_LO_LIM", 50), "e": en1})
    alm1 = p.block("DELAY", "DHW_TEMP_ALM", ["DHW_ALM_DLY", 0], public=True, module=m); p.wire(a1, alm1)
    p.wire(tv1, p.block("RO", "TV1_OUT", module=m)); p.wire(p1, p.block("BO", "P1_OUT", module=m))

    # 3 TC2_HEAT
    m = "TC2_HEAT"
    hot = x(m, "XPB", "SUM_ABOVE", "A>B", {"A": te2b_f, "B": sv(m, "SUM_STOP", 18)})
    hot_d = p.block("DELAY", "SUM_DELAYED", ["SUM_DLY", 0], module=m); p.wire(hot, hot_d)
    res = x(m, "XPB", "SUM_RESET", "A<B", {"A": te2b_f, "B": sv(m, "SUM_START", 16)})
    sset = x(m, "XPB", "SUM_SET", "d&!r", {"d": hot_d, "r": res})       # reset dominant: never set and reset together
    summer = p.block("SR", "SUMMER", [0], public=True, module=m); p.wire(sset, summer, "s"); p.wire(res, summer, "r")
    p2 = x(m, "XPB", "P2_RUN", "A>0.5&!s", {"A": sv(m, "HEAT_ENABLE", 1), "s": summer}, True)
    te2a = x(m, "XPR", "TE2A", "A", {"A": p.block("RI", "TE2A_IN", [0], module=m)}, True)
    f2a = x(m, "XPB", "TE2A_FAULT", "A<-20|A>120", {"A": te2a}, True)
    crv = p.block("CURVE", "HEAT_CURVE", [1, -20, "CRV_N20", 0, "CRV_0", 20, "CRV_P20"], module=m); p.wire(te2b_f, crv)
    sp2 = p.block("LIMIT", "HEAT_SP", ["TS_MIN", "TS_MAX"], public=True, module=m); p.wire(crv, sp2)
    pf2 = x(m, "XPB", "P2_FAULT", "A>0.5", {"A": p.block("RI", "P2_FLT_IN", [0], module=m)}, True)   # motor protection of P2 (HS)
    x(m, "XPI", "P2_ST", "f?2:(r?1:0)", {"f": pf2, "r": p2}, True)
    en2 = x(m, "XPB", "HEAT_CTRL_EN", "p&!f&!g", {"p": p2, "f": f2a, "g": pf2})   # no flow without P2: close TV2, do not waste district heat
    tv2 = pid(m, "TV2", te2a, sp2, en2, sv(m, "HEAT_PID_P", 40), sv(m, "HEAT_PID_I", 60))
    a2 = x(m, "XPB", "HEAT_ALM_RAW", "A>B|A<C", {"A": te2a, "B": sv(m, "HEAT_HI_LIM", 80), "C": sv(m, "HEAT_LO_LIM", 8)})
    alm2 = p.block("DELAY", "HEAT_TEMP_ALM", ["HEAT_ALM_DLY", 0], public=True, module=m); p.wire(a2, alm2)
    p.wire(tv2, p.block("RO", "TV2_OUT", module=m)); p.wire(p2, p.block("BO", "P2_OUT", module=m))

    # 4 ALARM
    m = "ALARM"
    s = x(m, "XPB", "ALARM_SUM", "a|b|c|d|e|f|g", {"a": f2b, "b": f1, "c": alm1, "d": f2a, "e": alm2, "f": pf1, "g": pf2}, True)
    p.wire(s, p.block("BO", "ALARM_OUT", module=m))
    return p


if __name__ == "__main__":
    p = build()
    p.save(os.path.join(HERE, "DH-ex2.aut"))
    bad = p.overlaps()
    json.dump(p.expected(), open(os.path.join(HERE, "expected.json"), "w"), indent=1)
    print(p.stats(), "overlaps:", bad)
    sys.exit(1 if bad else 0)
