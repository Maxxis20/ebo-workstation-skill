#!/usr/bin/env python3
"""AHU01 for EBO 7.1: controller program of a generic air handling unit, as one Function Block program text.

Specification: DESCRIPTION.md (sections 2 to 6) next to this file. Notes on the build, deviations and the test
plan: PROGRAM_NOTES.md.

    python3 make_program.py                       -> AHU01.aut, expected.json, io.json; stats and check on stdout
    python3 make_program.py --only Modes,Latches  -> AHU01_part.aut: only those groups, every signal they read
                                                     from another group comes from a public test value in
                                                     module Test (PVR / PVB, named as the signal)
    python3 make_program.py --list                -> the group names

The program is built in groups, one Python function each (an HFB, or a function group laid out flat on the top
level). A group reads signals of other groups by name (need), and offers its own by name (produce); the wires
between groups are made at the end, so the order of the groups does not matter and a group can be built alone.
"""
import argparse, json, os, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "..", "scripts")
sys.path.insert(0, LIB)
import aut                                                     # noqa: E402
from aut import Program, HFB, expr_inputs                       # noqa: E402

C = "\xb0C"


# --- work-around: ALARM reset text ---------------------------------------------------------------------------
# aut.Block.line writes the alarm text as both alarm and reset text. The specification wants "Alarm cleared" as
# the reset text, so the line is patched here (aut.py itself is left as it is).
_line = aut.Block.line


def _alarm_line(self):
    s = _line(self)
    rt = getattr(self, "reset_text", None)
    if self.typ == "ALARM" and rt is not None:
        text = self.params[3]
        s = s[: s.rindex(f"'{text}','{text}')")] + f"'{text}','{rt}')"
    return s


aut.Block.line = _alarm_line

# input pin kinds of catalogue blocks, for the kind of a test value in --only mode
_KINDS = {}
for _b in ET.parse(aut.CATALOGUE).getroot().iter("block"):
    _KINDS[_b.get("name")] = ["b" if i.get("type") == "binary" else ("i" if i.get("type") == "integer" else "a")
                              for i in _b.findall(".//input")]

# start values of the test values in --only mode (anything not listed starts at 0)
TEST_DEFAULT = {"TE00": 0, "TE1": 40, "TE2": 20, "TE3": 15, "TE4": 20, "TE5": 20, "TE6": 0, "TE7": 22, "TE8": 5,
                "TE10_1": 21, "TE10_2": 21, "TE10_3": 21, "OT": 0, "OT_OK": 1, "Room_Avg": 21, "Room_OK": 1,
                "OT_Day_Mean": 5, "FA01": 1, "SB01": 1, "SC3_Fault": 1, "P1_Fdb": 1, "TF01_Fdb": 1,
                "PF01_Fdb": 1, "PE1": 140, "PE2": 105, "Active_SP": 20, "Supply_Pressure_SP": 140,
                "Exhaust_Pressure_SP": 105}


class Builder:
    def __init__(self, only=None):
        self.p = Program("AHU01")
        self.only = only
        self.S = {}                       # signal name -> (source, kind 'a' / 'b' / 'i')
        self.pending = []                 # (signal name, destination block on the top level, pin, kind)
        self.ksig_cache = {}
        self.io = {"inputs": [], "outputs": [], "setpoints": [], "alarms": [], "states": [], "constants": []}
        self.test = {}

    # --- registry ----------------------------------------------------------------------------------------
    def produce(self, name, src, kind):
        if name in self.S:
            raise ValueError(f"signal {name} produced twice")
        self.S[name] = (src, kind)
        return src

    def need(self, name, dst, pin, kind=None):
        self.pending.append((name, dst, pin, kind or self._pin_kind(dst, pin)))

    def _pin_kind(self, dst, pin):
        if isinstance(dst, HFB):
            i = dst.in_names.index(pin) if isinstance(pin, str) else pin
            ins = [x for x in dst.inner.blocks if x.typ in ("HFAI", "HFDI")]
            return "b" if ins[i].typ == "HFDI" else "a"
        if dst.typ in aut.EXPR:
            return "a" if pin.isupper() else "b"
        if isinstance(pin, str):
            pin = aut.PINS[dst.typ][pin]
        return _KINDS[dst.typ][pin]

    def conn(self, d, src, dst, pin=0):
        if isinstance(src, str):
            if d is not self.p:
                raise ValueError(f"signal {src} asked for inside an HFB: route it through a pin")
            self.need(src, dst, pin)
        else:
            d.wire(src, dst, pin)

    def finish(self):
        for name, dst, pin, kind in self.pending:
            if name in self.S:
                self.p.wire(self.S[name][0], dst, pin)
                continue
            if not self.only:
                raise ValueError(f"signal {name} is read but nobody produces it")
            if name not in self.test:
                typ = {"a": "PVR", "b": "PVB", "i": "PVI"}[kind]
                self.test[name] = self.p.block(typ, name, params=[TEST_DEFAULT.get(name, 0)], public=True,
                                               module="Test")
            self.p.wire(self.test[name], dst, pin)

    # --- block helpers -----------------------------------------------------------------------------------
    @staticmethod
    def unit(u):
        return u if u in aut.UNITS else ""          # only units with a known EBO code go into the file

    def blk(self, d, typ, name="", params=(), ins=(), module="", public=None, unit="", **kw):
        """Block on level d (program or HFB); ins = [(pin, source)], source a block / port or a signal name."""
        if public is None:
            public = bool(name)
        b = d.block(typ, name, params=list(params), unit=self.unit(unit), public=public, module=module, **kw)
        for pin, src in ins:
            self.conn(d, src, b, pin)
        return b

    def xp(self, d, typ, expr, ins, name="", module="", public=None, unit=""):
        """Expression block; ins = {letter: source}. Checks the letters against the expression."""
        letters = expr_inputs(expr)
        if sorted(letters) != sorted(ins):
            raise ValueError(f"{expr!r}: letters {letters}, given {sorted(ins)}")
        if len(expr) > 60 or len(letters) > 8:
            raise ValueError(f"{expr!r}: too long ({len(expr)} characters, {len(letters)} inputs)")
        return self.blk(d, typ, name, [expr], list(ins.items()), module, public, unit)

    def delay(self, d, src, on, off, name="", module=""):
        return self.blk(d, "DELAY", name, [on, off], [(0, src)], module)

    def latch(self, d, name, module, set_expr, res_expr, ins):
        """Reset dominant SR: set input = set AND NOT reset (written out in set_expr), reset = res_expr."""
        s = self.xp(d, "XPB", set_expr, {k: v for k, v in ins.items() if k in expr_inputs(set_expr)})
        r = self.xp(d, "XPB", res_expr, {k: v for k, v in ins.items() if k in expr_inputs(res_expr)})
        return self.blk(d, "SR", name, [0], [("s", s), ("r", r)], module)

    def opr(self, d, v):
        return d.block("OpR", params=[v])

    def opb(self, d, v):
        return d.block("OpB", params=[v])

    # --- parameters --------------------------------------------------------------------------------------
    def sp(self, d, typ, name, value, unit, module, rng=""):
        """Operator setpoint: public, writable, backed up (flag 7)."""
        b = self.blk(d, typ, name, [value], module=module, public=True, unit=unit)
        self.io["setpoints"].append({"path": f"{module}/{name}", "default": value, "unit": unit,
                                     "type": typ, "range": rng})
        return b

    def econ(self, name, value, unit="", public=True):
        """Engineering constant (public) or private constant; made once, program wide."""
        if any(c[0] == name for c in self.p.consts):
            return name
        if len(name) > 20:
            raise ValueError(f"constant name {name} longer than 20")
        self.p.const(name, value, self.unit(unit), public=public)
        if public:
            self.io["constants"].append({"name": name, "default": value, "unit": unit})
        return name

    def ksig(self, d, name, value, unit=""):
        """A public constant as a signal: LIMIT (c, c) fed by a constant 0 always outputs c. Needed where an
        engineering constant enters an expression (public constants are refused inside expressions)."""
        key = (id(d), name)
        if key not in self.ksig_cache:
            c = self.econ(name, value, unit)
            self.ksig_cache[key] = self.blk(d, "LIMIT", "", [c, c], [(0, self.opr(d, 0))], unit=unit)
        return self.ksig_cache[key]

    def alarm(self, name, src, text, delay_on, cls):
        prio = {"A": 1, "B": 2, "C": 3}[cls]
        a = self.p.block("ALARM", name, [delay_on, 0, prio, text], public=True, module="Alarms")
        a.reset_text = "Alarm cleared"
        self.conn(self.p, src, a, 0)
        self.io["alarms"].append({"path": f"Alarms/{name}", "class": cls, "priority": prio, "text": text,
                                  "delay_s": delay_on, "condition": src if isinstance(src, str) else src.name})
        return a


# =============================================================================================================
# Groups. Each takes the builder and builds on the top level (and inside its own HFBs).
# =============================================================================================================
AI = [("TE00", C, "-50 ... 50"), ("TE1", C, "0 ... 100"), ("TE2", C, "-50 ... 100"), ("TE3", C, "-50 ... 50"),
      ("TE4", C, "-50 ... 80"), ("TE5", C, "-50 ... 80"), ("TE6", C, "-50 ... 50"), ("TE7", C, "-50 ... 100"),
      ("TE8", C, "-50 ... 50"), ("TE10_1", C, "0 ... 50"), ("TE10_2", C, "0 ... 50"), ("TE10_3", C, "0 ... 50"),
      ("PE1", "Pa", "0 ... 500"), ("PE2", "Pa", "0 ... 500"), ("PDE1", "Pa", "0 ... 500"),
      ("PDE2", "Pa", "0 ... 500"), ("PDE3", "Pa", "0 ... 500"), ("PDE4", "Pa", "0 ... 500"),
      ("PDE10", "Pa", "0 ... 2000"), ("PDE20", "Pa", "0 ... 2000")]
DI = ["FA01", "SB01", "HS10", "P1_Fdb", "TF01_Fdb", "PF01_Fdb", "SC3_Fault", "Reset_DI"]
TEMPS = ["TE00", "TE1", "TE2", "TE3", "TE4", "TE5", "TE6", "TE7", "TE8", "TE10_1", "TE10_2", "TE10_3"]


def g_inputs(B):
    """Physical inputs (RI / BI), soft binary inputs (BI), alarm reset (one-cycle DELB + rising edge)."""
    p = B.p
    for tag, u, rng in AI:
        B.produce(tag, B.blk(p, "RI", tag, module="Inputs", public=True, unit=u), "a")
        B.io["inputs"].append({"tag": tag, "kind": "AI", "unit": u, "range": rng, "block": f"Inputs/{tag}"})
    for tag in DI:
        B.produce(tag, B.blk(p, "BI", tag, module="Inputs", public=True), "b")
        B.io["inputs"].append({"tag": tag, "kind": "DI", "unit": "", "block": f"Inputs/{tag}"})
    for tag, mod in (("HN_Pres_In", "Inputs"), ("HN_Temp_In", "Inputs"),
                     ("Time_Schedule", "Operation"), ("Night_Schedule", "Operation")):
        B.produce(tag, B.blk(p, "BI", tag, module=mod, public=True), "b")
        B.io["inputs"].append({"tag": tag, "kind": "soft-binary", "unit": "", "block": f"{mod}/{tag}"})
    rc = B.blk(p, "DELB", "Reset_Cmd", [0], [(0, B.opb(p, 0))], module="Inputs", public=True)
    B.io["inputs"].append({"tag": "Reset_Cmd", "kind": "soft-binary", "unit": "", "block": "Inputs/Reset_Cmd",
                           "note": "write 1: one-cycle pulse, returns to 0 by itself"})
    either = B.xp(p, "XPB", "c|d", {"c": rc, "d": "Reset_DI"})
    B.produce("Reset_Pulse", B.blk(p, "TRIG", "Reset_Pulse", [1], [(0, either)], module="Inputs"), "b")


def g_sensorcheck(B):
    """HFB SensorCheck: instant fault flags of the 12 temperatures, outdoor value in use, room mean."""
    p = B.p
    h = p.hfb("SensorCheck", module="Inputs")
    pin = {t: h.inp(t) for t in TEMPS}
    for t in TEMPS:
        B.need(t, h, t)
    B.econ("MinTemp", -120, C, public=False)
    B.econ("MaxTemp", 120, C, public=False)
    bad = {t: B.xp(h, "XPB", "(A<MinTemp)|(A>MaxTemp)", {"A": pin[t]}, f"bad_{t}", "Inputs") for t in TEMPS}
    ot_ok = B.xp(h, "XPB", "!b", {"b": bad["TE00"]}, "OT_OK", "Inputs")
    ot = B.xp(h, "XPR", "b?C:A", {"A": pin["TE00"], "b": bad["TE00"], "C": B.ksig(h, "OT_Fault_Value", 0, C)},
              "OT", "Inputs", unit=C)
    r = [bad["TE10_1"], bad["TE10_2"], bad["TE10_3"]]
    n = B.xp(h, "XPR", "(a?0:1)+(b?0:1)+(c?0:1)", {"a": r[0], "b": r[1], "c": r[2]}, "Room_N", "Inputs")
    s = B.xp(h, "XPR", "(a?0:D)+(b?0:E)+(c?0:F)",
             {"a": r[0], "b": r[1], "c": r[2], "D": pin["TE10_1"], "E": pin["TE10_2"], "F": pin["TE10_3"]})
    room_ok = B.xp(h, "XPB", "N>0.5", {"N": n}, "Room_OK", "Inputs")
    room = B.xp(h, "XPR", "(N>0.5)?(S/N):0", {"N": n, "S": s}, "Room_Avg", "Inputs", unit=C)
    for t in TEMPS:
        B.produce(f"bad_{t}", h.out(f"bad_{t}", bad[t], binary=True), "b")
    B.produce("OT", h.out("OT", ot), "a")
    B.produce("OT_OK", h.out("OT_OK", ot_ok, binary=True), "b")
    B.produce("Room_Avg", h.out("Room_Avg", room), "a")
    B.produce("Room_OK", h.out("Room_OK", room_ok, binary=True), "b")


def g_daymean(B):
    """HFB DayMean: mean of the minute samples of OT over the previous day (5 degC until the first midnight)."""
    p = B.p
    h = p.hfb("DayMean", module="Inputs")
    ot, ok = h.inp("OT"), h.inp("OT_OK", binary=True)
    B.need("OT", h, "OT"); B.need("OT_OK", h, "OT_OK")
    mi = B.blk(h, "MINUTE")
    mi_prev = B.blk(h, "DELI", "", [0], [(0, mi)])
    hr = B.blk(h, "HOUR")
    hr_prev = B.blk(h, "DELI", "", [0], [(0, hr)])
    sample = B.xp(h, "XPB", "(ABS(M-N)>0.5)&o", {"M": mi, "N": mi_prev, "o": ok}, "DM_Sample", "Inputs")
    day = B.xp(h, "XPB", "H<G", {"H": hr, "G": hr_prev}, "DM_Day_Tick", "Inputs")
    s_in = B.xp(h, "XPR", "s?A:0", {"s": sample, "A": ot})
    c_in = B.xp(h, "XPR", "s?1:0", {"s": sample})
    clr = B.blk(h, "DELB", "", [0], [(0, day)])                          # clear one cycle after the copy
    tot = B.blk(h, "ACCUM", "DM_Sum", [0], [("i", s_in), ("rs", clr), ("rv", B.opr(h, 0))], module="Inputs")
    cnt = B.blk(h, "ACCUM", "DM_Cnt", [0], [("i", c_in), ("rs", clr), ("rv", B.opr(h, 0))], module="Inputs")
    tot_h = B.blk(h, "SHR", "DM_Sum_Held", [5], [("D", tot), ("c", day)], module="Inputs")
    cnt_h = B.blk(h, "SHR", "DM_Cnt_Held", [1], [("D", cnt), ("c", day)], module="Inputs")
    mean = B.xp(h, "XPR", "(C>0.5)?(S/C):5", {"C": cnt_h, "S": tot_h}, "OT_Day_Mean", "Inputs", unit=C)
    B.produce("OT_Day_Mean", h.out("OT_Day_Mean", mean), "a")


def g_modes(B):
    """HFB Modes: season, normal operation, night cooling, night heating, Run, Run_Mode."""
    p = B.p
    aom = B.sp(p, "PVI", "AOM", 2, "", "Operation", "0 off / 1 manual on / 2 automatic")
    sel = B.sp(p, "PVI", "Season_Sel", 0, "", "Operation", "0 auto / 1 heating / 2 cooling")
    B.io["inputs"] += [{"tag": "AOM", "kind": "soft-analog", "unit": "", "block": "Operation/AOM"},
                       {"tag": "Season_Sel", "kind": "soft-analog", "unit": "", "block": "Operation/Season_Sel"}]
    h = p.hfb("Modes", module="Operation")
    pins = {}
    for nm, b in (("AOM", 0), ("Season_Sel", 0), ("OT_Day_Mean", 0), ("Time_Schedule", 1), ("HS10", 1),
                  ("Night_Schedule", 1), ("Critical_Alarm", 1), ("OT", 0), ("OT_OK", 1), ("Room_Avg", 0),
                  ("Room_OK", 1)):
        pins[nm] = h.inp(nm, binary=bool(b))
    p.wire(aom, h, "AOM"); p.wire(sel, h, "Season_Sel")
    for nm in pins:
        if nm not in ("AOM", "Season_Sel"):
            B.need(nm, h, nm)
    M, dm, ot, ra = pins["AOM"], pins["OT_Day_Mean"], pins["OT"], pins["Room_Avg"]
    crit, otok, rok = pins["Critical_Alarm"], pins["OT_OK"], pins["Room_OK"]
    O = "Operation"
    # 4.3 season
    cool_ot = B.sp(h, "PVR", "Season_Cool_OT", 11, C, O, "5 ... 20")
    heat_ot = B.sp(h, "PVR", "Season_Heat_OT", 9, C, O, "0 ... 15")
    auto = B.latch(h, "Auto_Season", O, "(M>=C)&!(M<=H)", "M<=H", {"M": dm, "C": cool_ot, "H": heat_ot})
    season = B.xp(h, "XPB", "(S>1.5)|((S<0.5)&a)", {"S": pins["Season_Sel"], "a": auto}, "Season_Mode", O)
    # 4.4 normal operation
    ext = B.delay(h, pins["HS10"], 0, B.econ("HS10_Run_Time", 3600, "s"), "HS10_Ext", O)
    oper = B.xp(h, "XPB", "!c&(((M>0.5)&(M<1.5))|((M>1.5)&(t|x)))",
                {"c": crit, "M": M, "t": pins["Time_Schedule"], "x": ext}, "Operation", O)
    dly = B.econ("Night_Cond_Delay", 60, "s")
    # 4.6 night cooling
    nc_start = B.sp(h, "PVR", "Night_Cool_Start_T", 22, C, O, "20 ... 30")
    nc_stop = B.sp(h, "PVR", "Night_Cool_Stop_T", 19, C, O, "15 ... 25")
    nc_min = B.sp(h, "PVR", "Night_Cool_OT_Min", 12, C, O, "0 ... 20")
    nc_max = B.sp(h, "PVR", "Night_Cool_OT_Max", 19, C, O, "10 ... 25")
    nc_mode = B.sp(h, "PVB", "Night_Cool_Mode", 1, "", O, "0 / 1")
    ins = {"A": ra, "B": nc_start, "C": nc_stop, "o": oper, "k": rok}
    nc_room = B.latch(h, "NC_Room", O, "(A>=B)&!((A<=C)|o|!k)", "(A<=C)|o|!k", ins)
    nc_ot = B.xp(h, "XPB", "o&(A>=B)&(A<=C)", {"o": otok, "A": ot, "B": nc_min, "C": nc_max}, "NC_OT", O)
    nc_ot_d = B.delay(h, nc_ot, dly, dly, "NC_OT_D", O)
    nc_room_d = B.delay(h, nc_room, dly, dly, "NC_Room_D", O)
    ncool = B.xp(h, "XPB", "(M>1.5)&!o&!c&s&n&e&a&b",
                 {"M": M, "o": oper, "c": crit, "s": season, "n": pins["Night_Schedule"], "e": nc_mode,
                  "a": nc_ot_d, "b": nc_room_d}, "Night_Cooling", O)
    # 4.6 night heating
    nh_start = B.sp(h, "PVR", "Night_Heat_Start_T", 18, C, O, "15 ... 22")
    nh_stop = B.sp(h, "PVR", "Night_Heat_Stop_T", 20, C, O, "17 ... 25")
    nh_min = B.sp(h, "PVR", "Night_Heat_OT_Min", -15, C, O, "-30 ... 0")
    nh_max = B.sp(h, "PVR", "Night_Heat_OT_Max", 0, C, O, "-10 ... 10")
    nh_mode = B.sp(h, "PVB", "Night_Heat_Mode", 1, "", O, "0 / 1")
    ins = {"A": ra, "B": nh_start, "C": nh_stop, "o": oper, "k": rok}
    nh_room = B.latch(h, "NH_Room", O, "(A<=B)&!((A>=C)|o|!k)", "(A>=C)|o|!k", ins)
    nh_room_d = B.delay(h, nh_room, dly, dly, "NH_Room_D", O)
    nh_ot = B.xp(h, "XPB", "(M>=B)&(M<=C)", {"M": dm, "B": nh_min, "C": nh_max}, "NH_OT", O)
    nh_cond = B.xp(h, "XPB", "k&b&d", {"k": otok, "b": nh_ot, "d": nh_room_d}, "NH_Cond", O)
    nheat = B.xp(h, "XPB", "(M>1.5)&!o&!c&!s&n&e&k",
                 {"M": M, "o": oper, "c": crit, "s": season, "n": pins["Night_Schedule"], "e": nh_mode,
                  "k": nh_cond}, "Night_Heating", O)
    run = B.xp(h, "XPB", "!c&(o|n|h)", {"c": crit, "o": oper, "n": ncool, "h": nheat}, "Run", O)
    mode = B.xp(h, "XPI", "c?4:(o?1:(n?2:(h?3:0)))", {"c": crit, "o": oper, "n": ncool, "h": nheat},
                "Run_Mode", O)
    B.produce("Season_Mode", h.out("Season_Mode", season, binary=True), "b")
    B.produce("Operation", h.out("Operation", oper, binary=True), "b")
    B.produce("Night_Cooling", h.out("Night_Cooling", ncool, binary=True), "b")
    B.produce("Night_Heating", h.out("Night_Heating", nheat, binary=True), "b")
    B.produce("Run", h.out("Run", run, binary=True), "b")
    B.produce("Run_Mode", h.out("Run_Mode", mode), "i")


def crit_latch(B, latch_name):
    """HFB CritLatch: Latched = SR(set: Cause, reset: Reset_Pulse AND NOT Cause). The set input needs no
    gating: set AND NOT reset = Cause, since reset is false whenever Cause is true."""
    h = B.p.hfb("CL_" + latch_name[:-6], module="Alarms")
    cause, rp = h.inp("Cause", binary=True), h.inp("Reset_Pulse", binary=True)
    r = B.xp(h, "XPB", "p&!c", {"p": rp, "c": cause})
    sr = B.blk(h, "SR", latch_name, [0], [("s", cause), ("r", r)], module="Alarms")
    h.out("Latched", sr, binary=True)
    return h


def g_latches(B):
    """Critical causes, 8 x CritLatch, Critical_Alarm, Freeze_Group."""
    p = B.p
    A = "Alarms"
    fsp = B.sp(p, "PVR", "Freeze_SP", 6, C, "Inputs", "3 ... 10")
    sft = B.sp(p, "PVR", "Supply_Fire_Temp", 50, C, A)
    eft = B.sp(p, "PVR", "Exhaust_Fire_Temp", 50, C, A)
    causes = [
        ("Freeze_Latch", B.xp(p, "XPB", "(A<=B)|c|(r&((D<=B)|e))",
                              {"A": "TE1", "B": fsp, "c": "bad_TE1", "r": "Run", "D": "TE2", "e": "bad_TE2"},
                              "Freeze_Cause", A)),
        ("Fire_Latch", B.xp(p, "XPB", "!a", {"a": "FA01"}, "Fire_Cause", A)),
        ("Stop_Latch", B.xp(p, "XPB", "!a", {"a": "SB01"}, "Stop_Cause", A)),
        ("P1_Latch", "P1_Fault_Cond"),
        ("HN_Pres_Latch", "HN_Pres_In"),
        ("HN_Temp_Latch", "HN_Temp_In"),
        ("Supply_Fire_Latch", B.xp(p, "XPB", "A>=B", {"A": "TE2", "B": sft}, "Supply_Fire_Cause", A)),
        ("Exhaust_Fire_Latch", B.xp(p, "XPB", "A>=B", {"A": "TE7", "B": eft}, "Exhaust_Fire_Cause", A)),
    ]
    outs = []
    for name, cause in causes:
        h = crit_latch(B, name)
        B.conn(p, cause, h, "Cause")
        B.need("Reset_Pulse", h, "Reset_Pulse")
        outs.append(B.produce(name, h.o("Latched"), "b"))
    crit = B.xp(p, "XPB", "a|b|c|d|e|f|g|h", dict(zip("abcdefgh", outs)), "Critical_Alarm", A)
    B.produce("Critical_Alarm", crit, "b")
    B.produce("Freeze_Group", B.xp(p, "XPB", "a|b", {"a": outs[0], "b": outs[3]}, "Freeze_Group", A), "b")


def fan_ctrl(B, pre, k):
    """HFB FanCtrl, once per fan. pre = Supply / Exhaust; k = names of its engineering constants."""
    h = B.p.hfb("FanCtrl_" + pre, module="FAN")
    P = {}
    for nm, b in (("Run", 1), ("Critical_Alarm", 1), ("PV", 0), ("Pressure_Set", 0), ("Low_Speed_Cmd", 1),
                  ("Low_Speed_SP", 0), ("Gain", 0), ("Ti", 0), ("Td", 0), ("DZ", 0), ("Fdb", 1), ("K", 0),
                  ("PDE", 0), ("Pres_Dev", 0)):
        P[nm] = h.inp(nm, binary=bool(b))
    F = "FAN"
    rel_in = B.xp(h, "XPB", "r&!c", {"r": P["Run"], "c": P["Critical_Alarm"]})
    rel = B.delay(h, rel_in, k["delay"], 0, f"{pre}_Released", F)
    psp = B.xp(h, "XPR", "c?B:A", {"c": P["Low_Speed_Cmd"], "B": P["Low_Speed_SP"], "A": P["Pressure_Set"]},
               f"{pre}_Pressure_SP", F, unit="Pa")
    mode = B.xp(h, "XPI", "a?1:3", {"a": rel})
    pid = B.blk(h, "PIDP", f"{pre}_PIDP", [k["int"], k["min"], k["max"], k["stroke"]], module=F, unit="%")
    for pin, src in (("MV", P["PV"]), ("SP", psp), ("Mode", mode), ("G", P["Gain"]), ("Ti", P["Ti"]),
                     ("Td", P["Td"]), ("DZ", P["DZ"]), ("TSg", pid)):
        h.wire(src, pid, pin)
    lim = B.blk(h, "LIMIT", "", [k["min"], k["max"]], [(0, pid)], unit="%")
    speed = B.xp(h, "XPR", "r?A:0", {"r": rel, "A": lim}, f"{pre}_Speed", F, unit="%")
    flow = B.xp(h, "XPR", "r?(B*SQRT((A>0)?A:0)/1000):0", {"r": P["Run"], "A": P["PDE"], "B": P["K"]},
                f"{pre}_Flow", "Inputs")
    dev = B.xp(h, "XPB", "r&((ABS(A-B)*100)>(C*B))", {"r": rel, "A": P["PV"], "B": psp, "C": P["Pres_Dev"]},
               f"{pre}_Pres_Cond", F)
    fdb = B.xp(h, "XPB", "r&!f", {"r": rel, "f": P["Fdb"]}, f"{pre}_Fdb_Cond", F)
    h.out("Released", rel, binary=True); h.out("Speed", speed); h.out("Flow", flow)
    h.out("Pres_Dev_Cond", dev, binary=True); h.out("Fdb_Fault_Cond", fdb, binary=True)
    h.out("Pressure_SP", psp)
    return h


def g_fan(B):
    """Low speed mode, pressure setpoint curves, both FanCtrl."""
    p = B.p
    F = "FAN"
    lsm = B.sp(p, "PVB", "Low_Speed_Mode", 0, "", F, "0 / 1")
    lst = B.sp(p, "PVR", "Low_Speed_Temp_SP", -10, C, F, "-30 ... 0")
    lsd = B.sp(p, "PVR", "Low_Speed_Deviation", 2, "K", F, "0.5 ... 5")
    cold = B.latch(p, "Cold", F, "(A<=B)&!(A>=(B+C))", "A>=(B+C)", {"A": "OT", "B": lst, "C": lsd})
    lsc_in = B.xp(p, "XPB", "c&m", {"c": cold, "m": lsm})
    lsc = B.delay(p, lsc_in, 0, B.econ("Low_Speed_Delay_Off", 600, "s"), "Low_Speed_Cmd", F)
    curves = {}
    for pre, xs, ys, pts in (("Supply", "Temp_X", "Press_Y", [(-20, 50), (-15, 65), (-10, 75), (-5, 80)]),
                             ("Exhaust", "Temp1_X", "Press1_Y", [(-20, 40), (-15, 50), (-10, 55), (-5, 60)])):
        par = [1]
        for i, (x, y) in enumerate(pts, 1):
            par += [B.econ(f"{xs}{i}", x, C), B.econ(f"{ys}{i}", y, "Pa")]
        curves[pre] = B.blk(p, "CURVE", f"{pre}_LowSpd_SP", par, [(0, "OT")], module=F, unit="Pa")
    for pre, pv, fdb, pde, kname, set_, tag in (("Supply", "PE1", "TF01_Fdb", "PDE10", "TF01_K", 80, "TF01"),
                                                 ("Exhaust", "PE2", "PF01_Fdb", "PDE20", "PF01_K", 60, "PF01")):
        k = {"delay": B.econ(f"{pre}_Fan_Delay", 60 if pre == "Supply" else 30, "s"),
             "int": B.econ(f"{pre}_ControlInt", 1, "s"),
             "min": B.econ(f"{pre}_Ctrl_Min_SP", 20, "%"), "max": B.econ(f"{pre}_Ctrl_Max_SP", 60, "%"),
             "stroke": B.econ(f"{pre}_StrokeTime", 20, "s")}
        pset = B.sp(p, "PVR", f"{pre}_Pressure_Set", set_, "Pa", F, "20 ... 400")
        gain = B.sp(p, "PVR", f"{pre}_Gain", 0.05, "%/Pa", F, "0.001 ... 1")
        ti = B.sp(p, "PVR", f"{pre}_Integral_T", 60, "s", F, "5 ... 600")
        td = B.sp(p, "PVR", f"{pre}_Deriv_Time", 0, "s", F, "0 ... 60")
        dz = B.sp(p, "PVR", f"{pre}_Dead_Zone", 1, "Pa", F, "0 ... 10")
        kk = B.sp(p, "PVR", kname, 350, "", "Inputs", "1 ... 2000")
        dev = B.sp(p, "PVR", f"{pre}_Pres_Dev", 25, "%", "Alarms")
        h = fan_ctrl(B, pre, k)
        for pin, src in (("Run", "Run"), ("Critical_Alarm", "Critical_Alarm"), ("PV", pv), ("Pressure_Set", pset),
                         ("Low_Speed_Cmd", lsc), ("Low_Speed_SP", curves[pre]), ("Gain", gain), ("Ti", ti),
                         ("Td", td), ("DZ", dz), ("Fdb", fdb), ("K", kk), ("PDE", pde), ("Pres_Dev", dev)):
            B.conn(p, src, h, pin)
        B.produce(f"{pre}_Released", h.o("Released"), "b")
        B.produce(f"{pre}_Speed", h.o("Speed"), "a")
        B.produce(f"{pre}_Flow", h.o("Flow"), "a")
        B.produce(f"{pre}_Pres_Cond", h.o("Pres_Dev_Cond"), "b")
        B.produce(f"{pre}_Fdb_Cond", h.o("Fdb_Fault_Cond"), "b")
        B.produce(f"{pre}_Pressure_SP", h.o("Pressure_SP"), "a")


def filter_alarm(B, tag):
    """HFB FilterAlarm: Alarm_Cond = Enable AND Released AND DP > CURVE(Fan_Speed; X1,Y1; X2,Y2)."""
    h = B.p.hfb("FA_" + tag, module="Alarms")
    en, rel = h.inp("Enable", binary=True), h.inp("Released", binary=True)
    dp, spd = h.inp("DP"), h.inp("Fan_Speed")
    par = [1, B.econ(f"{tag}_X1", 0, "%"), B.econ(f"{tag}_Y1", 10, "Pa"),
           B.econ(f"{tag}_X2", 100, "%"), B.econ(f"{tag}_Y2", 150, "Pa")]
    lim = B.blk(h, "CURVE", f"{tag}_Limit", par, [(0, spd)], module="Alarms", unit="Pa")
    cond = B.xp(h, "XPB", "e&r&(A>B)", {"e": en, "r": rel, "A": dp, "B": lim}, f"{tag}_Cond", "Alarms")
    h.out("Alarm_Cond", cond, binary=True)
    return h


def g_filters(B):
    p = B.p
    for tag, rel, spd in (("PDE3", "Supply_Released", "TF01_Ctrl"), ("PDE1", "Supply_Released", "TF01_Ctrl"),
                          ("PDE2", "Exhaust_Released", "PF01_Ctrl")):
        en = B.sp(p, "PVB", f"{tag}_Filter", 1, "", "Alarms", "0 / 1")
        h = filter_alarm(B, tag)
        p.wire(en, h, "Enable")
        B.need(rel, h, "Released"); B.need(tag, h, "DP"); B.need(spd, h, "Fan_Speed")
        B.produce(f"{tag}_Cond", h.o("Alarm_Cond"), "b")


def g_tempseq(B):
    """HFB TempSeq: supply setpoint, one controller per heating / cooling stage with staging, start-up pre-heat."""
    p = B.p
    hm = B.sp(p, "PVB", "Heating_Mode", 0, "", "Operation", "0 / 1")
    B.io["inputs"].append({"tag": "Heating_Mode", "kind": "soft-binary", "unit": "", "block": "Operation/Heating_Mode"})
    h = p.hfb("TempSeq", module="ST")
    P = {}
    for nm, b in (("TE2", 0), ("TE7", 0), ("OT", 0), ("OT_OK", 1), ("bad_TE7", 1), ("Run", 1), ("Season_Mode", 1),
                  ("Operation", 1), ("Night_Cooling", 1), ("Night_Heating", 1), ("Heating_Mode", 1)):
        P[nm] = h.inp(nm, binary=bool(b))
    p.wire(hm, h, "Heating_Mode")
    for nm in P:
        if nm != "Heating_Mode":
            B.need(nm, h, nm)
    S = "ST"
    s, te2, te7, ot = P["Season_Mode"], P["TE2"], P["TE7"], P["OT"]
    # 4.9 setpoint
    x1 = B.sp(h, "PVR", "ET_X1", 18, C, S); y1 = B.sp(h, "PVR", "SP_Y1", 21.5, C, S)
    x2 = B.sp(h, "PVR", "ET_X2", 23, C, S); y2 = B.sp(h, "PVR", "SP_Y2", 16, C, S)
    fsp = B.sp(h, "PVR", "ST_Fault_SP", 19, C, S, "15 ... 25")
    crv = B.xp(h, "XPR", "(A<=B)?C:((A>=D)?E:(C+((E-C)*(A-B)/(D-B))))",
               {"A": te7, "B": x1, "C": y1, "D": x2, "E": y2}, "Temp_SP_Curve", S, unit=C)
    tsp = B.xp(h, "XPR", "f?B:A", {"f": P["bad_TE7"], "B": fsp, "A": crv}, "Temp_SP", S, unit=C)
    nhs = B.sp(h, "PVR", "Night_Heat_ST", 27, C, S, "18 ... 35")
    ncs = B.sp(h, "PVR", "Night_Cool_ST", 17, C, S, "15 ... 25")
    nhl = B.blk(h, "LIMIT", "", [B.econ("Night_Heat_Min_Temp", 18, C), B.econ("Night_Heat_Max_Temp", 35, C)],
                [(0, nhs)], unit=C)
    ncl = B.blk(h, "LIMIT", "", [B.econ("Night_Cool_Min_Temp", 15, C), B.econ("Night_Cool_Max_Temp", 25, C)],
                [(0, ncs)], unit=C)
    heat_sp = B.xp(h, "XPR", "n?B:A", {"n": P["Night_Heating"], "B": nhl, "A": tsp}, "Heat_Temp_SP", S, unit=C)
    cool_sp = B.xp(h, "XPR", "n?B:A", {"n": P["Night_Cooling"], "B": ncl, "A": tsp}, "Cool_Temp_SP", S, unit=C)
    act_sp = B.xp(h, "XPR", "s?B:A", {"s": s, "A": heat_sp, "B": cool_sp}, "Active_SP", S, unit=C)
    # 4.10 controllers
    heat_act = B.xp(h, "XPB", "!s&(o|n)", {"s": s, "o": P["Operation"], "n": P["Night_Heating"]}, "Heat_Active", S)
    cool_act = B.xp(h, "XPB", "s&(o|n)", {"s": s, "o": P["Operation"], "n": P["Night_Cooling"]}, "Cool_Active", S)
    rise = B.blk(h, "TRIG", "", [1], [(0, P["Run"])])
    ph_st = B.sp(h, "PVR", "PreHeat_Heat_ST", 9, C, S, "-10 ... 15")
    ph_in = B.xp(h, "XPB", "t&(A<=B)&!s", {"t": rise, "A": ot, "B": ph_st, "s": s})
    ph = B.delay(h, ph_in, 0, B.econ("PreHeat_Heat_Delay", 1, "s"), "PreHeat_Pulse", S)
    ph_hold = B.delay(h, ph, 0, B.econ("HRU_Preheat_Del", 1200, "s"))
    hold = B.xp(h, "XPB", "r&h", {"r": P["Run"], "h": ph_hold}, "HRU_Hold", S)
    # cooling recovery: the extract air is cooler than the outdoor air, so the rotor cools the supply air
    hist = B.sp(h, "PVR", "Cool_Recovery_Hist", 2, "K", S, "0.5 ... 5")
    cr = B.latch(h, "Cool_Recovery", S, "!f&o&(B<=(A-D))&!(B>=(A+D))", "(B>=(A+D))|f|!o",
                 {"A": ot, "B": te7, "D": hist, "f": P["bad_TE7"], "o": P["OT_OK"]})
    hmp = P["Heating_Mode"]
    # 4.10 one controller per stage, one of them in control at a time. Heating side: rotor -> cooling coil with warm
    # water (Heating_Mode) -> heating coil. Cooling side (cooling season): rotor (cooling recovery) -> cooling valve.
    # A stage is released when the one before it has been at 100 % for Stage_Up_Delay and handed back when its own
    # output has been at 0 for Stage_Down_Delay; stages below the one in control stay at 100 %, those above at 0.
    td = B.sp(h, "PVR", "Temp_Derivative_Time", 0, "s", S, "0 ... 60")
    dz = B.sp(h, "PVR", "Temp_Dead_Zone", 0.1, "K", S, "0 ... 1")
    nz = B.sp(h, "PVR", "Neutral_Zone", 0.5, "K", S, "0.2 ... 3")
    up, dn = B.econ("Stage_Up_Delay", 30, "s"), B.econ("Stage_Down_Delay", 30, "s")
    act = B.xp(h, "XPB", "a|b", {"a": heat_act, "b": cool_act}, "Temp_Active", S)
    rc = B.xp(h, "XPB", "c&s", {"c": cr, "s": s}, "Rotor_Cools", S)
    av2 = B.xp(h, "XPB", "!s&m", {"s": s, "m": hmp}, "CCH_Avail", S)
    L2 = B.blk(h, "SR", "Stage_CCH", [0], module=S)          # cooling coil released as a heater
    L3 = B.blk(h, "SR", "Stage_HC", [0], module=S)           # heating coil released
    Lc = B.blk(h, "SR", "Cool_Side", [0], module=S)          # cooling side in control
    Lv = B.blk(h, "SR", "Stage_Cool", [0], module=S)         # cooling valve released
    hsd = B.xp(h, "XPB", "(a|p)&!k", {"a": act, "p": ph, "k": Lc}, "Heat_Side", S)
    pid = {n: B.blk(h, "PIDA", f"{n}_PIDA", [1, 0, 100, 0], module=S, unit="%") for n in ("HRU", "CCH", "HC", "Cool")}
    tune = {n: (B.sp(h, "PVR", f"{n}_Gain", g, "", S, "0.1 ... 20"), B.sp(h, "PVR", f"{n}_Ti", t, "s", S, "10 ... 600"))
            for n, g, t in (("HRU", 1.5, 45), ("CCH", 2, 45), ("HC", 1.5, 45), ("Cool", 2.5, 45))}
    # which controller is in control (act) and which outputs are held at 100 % (full)
    r_act = B.xp(h, "XPB", "(h&!r&!b&!c)|(k&r&!d)", {"h": hsd, "r": rc, "b": L2, "c": L3, "k": Lc, "d": Lv}, "HRU_Act", S)
    r_full = B.xp(h, "XPB", "(h&!r&(b|c))|(k&r&d)", {"h": hsd, "r": rc, "b": L2, "c": L3, "k": Lc, "d": Lv})
    c_act = B.xp(h, "XPB", "h&b&!c", {"h": hsd, "b": L2, "c": L3}, "CCH_Act", S)
    c_full = B.xp(h, "XPB", "h&b&c", {"h": hsd, "b": L2, "c": L3})
    h_act = B.xp(h, "XPB", "h&c", {"h": hsd, "c": L3}, "HC_Act", S)
    v_act = B.xp(h, "XPB", "k&d", {"k": Lc, "d": Lv}, "Cool_Act", S)
    phv = B.xp(h, "XPR", "m?B:A", {"m": hmp, "A": B.ksig(h, "PreHeat_Valve", 75, "%"),
                                   "B": B.ksig(h, "PreHeat_Valve_HM", 50, "%")})
    sc3 = B.xp(h, "XPR", "e?A:(f?100:0)", {"e": r_act, "A": pid["HRU"], "f": r_full}, "SC3_Seq", S, unit="%")
    u_cch = B.xp(h, "XPR", "e?A:(f?100:0)", {"e": c_act, "A": pid["CCH"], "f": c_full}, "TV2_Heat_Seq", S, unit="%")
    tv1 = B.xp(h, "XPR", "p?V:(e?A:0)", {"p": ph, "V": phv, "e": h_act, "A": pid["HC"]}, "TV1_Seq", S, unit="%")
    u_cv = B.xp(h, "XPR", "e?A:0", {"e": v_act, "A": pid["Cool"]}, "TV2_Cool_Seq", S, unit="%")
    tv2 = B.xp(h, "XPR", "A+B", {"A": u_cch, "B": u_cv}, "TV2_Seq", S, unit="%")
    # the rotor and the cooling valve cool: measured value and setpoint change places, so the output rises when the
    # supply air is too warm
    r_mv = B.xp(h, "XPR", "r?B:A", {"r": rc, "A": te2, "B": act_sp})
    r_sp = B.xp(h, "XPR", "r?A:B", {"r": rc, "A": te2, "B": act_sp})
    for n, mv, spv, a_, out in (("HRU", r_mv, r_sp, r_act, sc3), ("CCH", te2, act_sp, c_act, u_cch),
                                ("HC", te2, act_sp, h_act, tv1), ("Cool", act_sp, te2, v_act, u_cv)):
        mode = B.xp(h, "XPI", "a?1:0", {"a": a_})
        for pin, src in (("MV", mv), ("SP", spv), ("Mode", mode), ("TSg", out), ("G", tune[n][0]), ("Ti", tune[n][1]),
                         ("Td", td), ("DZ", dz)):
            h.wire(src, pid[n], pin)
    # stage latches (reset dominant)
    def stage(L, set_raw, set_now, low, res_other):
        sd = B.delay(h, set_raw, up, 0); ld = B.delay(h, low, dn, 0)
        r = B.xp(h, "XPB", "d|x", {"d": ld, "x": res_other})
        st = B.xp(h, "XPB", "(d|n)&!r", {"d": sd, "n": set_now, "r": r})
        h.wire(st, L, "s"); h.wire(r, L, "r")
    q_r = B.xp(h, "XPB", "r|(A>=99.5)", {"r": rc, "A": sc3})                       # rotor at 100 %, or not a heater now
    stage(L2, B.xp(h, "XPB", "h&v&q&!b", {"h": hsd, "v": av2, "q": q_r, "b": L2}),
          B.xp(h, "XPB", "p&v", {"p": ph, "v": av2}),
          B.xp(h, "XPB", "b&(A<=0.5)&!c&!r", {"b": L2, "A": u_cch, "c": L3, "r": rc}),
          B.xp(h, "XPB", "!v|!h", {"v": av2, "h": hsd}))
    q3 = B.xp(h, "XPB", "(v&b&(A>=99.5))|(!v&q)", {"v": av2, "b": L2, "A": u_cch, "q": q_r})
    stage(L3, B.xp(h, "XPB", "h&q&!c", {"h": hsd, "q": q3, "c": L3}), ph,
          B.xp(h, "XPB", "c&(A<=0.5)&(v|!r)&!p", {"c": L3, "A": tv1, "v": av2, "r": rc, "p": ph}),
          B.xp(h, "XPB", "!h", {"h": hsd}))
    hsum = B.xp(h, "XPR", "A+B+C", {"A": tv1, "B": u_cch, "C": sc3})
    csum = B.xp(h, "XPR", "A+B", {"A": u_cv, "B": sc3})
    never = B.xp(h, "XPB", "k&!k", {"k": Lc})
    stage(Lc, B.xp(h, "XPB", "e&!k&(S<=0.5)&(T>(P+N))", {"e": cool_act, "k": Lc, "S": hsum, "T": te2, "P": act_sp, "N": nz}),
          never,
          B.xp(h, "XPB", "k&(S<=0.5)&(T<(P-N))", {"k": Lc, "S": csum, "T": te2, "P": act_sp, "N": nz}),
          B.xp(h, "XPB", "!e", {"e": cool_act}))
    stage(Lv, B.xp(h, "XPB", "k&!d&r&(A>=99.5)", {"k": Lc, "d": Lv, "r": rc, "A": sc3}),
          B.xp(h, "XPB", "k&!r", {"k": Lc, "r": rc}),
          B.xp(h, "XPB", "d&r&(A<=0.5)", {"d": Lv, "r": rc, "A": u_cv}),
          B.xp(h, "XPB", "!k", {"k": Lc}))
    for nm, src, b in (("Active_SP", act_sp, 0), ("SC3_Seq", sc3, 0), ("TV1_Seq", tv1, 0), ("TV2_Seq", tv2, 0),
                       ("PreHeat_Pulse", ph, 1), ("HRU_Hold", hold, 1), ("Cool_Recovery", cr, 1)):
        B.produce(nm, h.out(nm, src, binary=bool(b)), "b" if b else "a")


def g_coil(B):
    """HFB CoilProtect: coil return water minimum control, forced open by Freeze_Group."""
    p = B.p
    h = p.hfb("CoilProtect", module="ST")
    te1, fg = h.inp("TE1"), h.inp("Freeze_Group", binary=True)
    B.need("TE1", h, "TE1"); B.need("Freeze_Group", h, "Freeze_Group")
    S = "ST"
    cst = B.sp(h, "PVR", "Coil_Heat_ST", 10, C, S, "5 ... 30")
    diff = B.xp(h, "XPR", "A-B", {"A": te1, "B": cst})
    above = B.blk(h, "HYST", "", [B.econ("Coil_Heat_OFF_SP", 12, "K"), B.econ("Coil_Heat_ON_SP", 10, "K")],
                  [(0, diff)])
    en = B.xp(h, "XPB", "!a", {"a": above}, "Coil_En", S)
    mode = B.xp(h, "XPI", "f?2:(e?1:3)", {"f": fg, "e": en})
    pid = B.blk(h, "PIDA", "Coil_Heat_PIDA", [1, 0, 100, 0], module=S, unit="%")
    for pin, src in (("MV", te1), ("SP", cst), ("Mode", mode), ("TSg", pid), ("G", B.ksig(h, "Coil_Gain", 5)),
                     ("Ti", B.ksig(h, "Coil_Ti", 60, "s")), ("Td", B.opr(h, 0)), ("DZ", B.opr(h, 0.1))):
        h.wire(src, pid, pin)
    out = B.xp(h, "XPR", "(f|e)?A:0", {"f": fg, "e": en, "A": pid}, "Coil_Heat_Ctrl", S, unit="%")
    B.produce("Coil_Heat_Ctrl", h.out("Coil_Heat_Ctrl", out), "a")


def g_hru(B):
    """HFB HruFrostEff: rotor frost protection and temperature efficiency."""
    p = B.p
    h = p.hfb("HruFrostEff", module="HRU")
    P = {}
    for nm, b in (("PDE4", 0), ("PF01_Ctrl", 0), ("TE3", 0), ("TE6", 0), ("TE7", 0), ("SC3_Ctrl", 0), ("Run", 1),
                  ("bad_TE3", 1), ("bad_TE6", 1), ("bad_TE7", 1)):
        P[nm] = h.inp(nm, binary=bool(b))
        B.need(nm, h, nm)
    H, A = "HRU", "Alarms"
    pdef = B.sp(h, "PVB", "PDE4_Frost", 1, "", A, "0 / 1")
    pft = B.sp(h, "PVR", "PDE4_Frost_Temp", 0, C, A)
    par = [1, B.econ("PDE4_X1", 0, "%"), B.econ("PDE4_Y1", 100, "Pa"), B.econ("PDE4_X2", 100, "%"),
           B.econ("PDE4_Y2", 300, "Pa")]
    psp = B.blk(h, "CURVE", "PDE4_SP", par, [(0, P["PF01_Ctrl"])], module=H, unit="Pa")
    fc = B.xp(h, "XPB", "e&r&((A<=B)|f)&(C>D)",
              {"e": pdef, "r": P["Run"], "A": P["TE6"], "B": pft, "f": P["bad_TE6"], "C": P["PDE4"], "D": psp},
              "Frost_Cond", H)
    fa = B.delay(h, fc, 0, B.econ("Frost_Hold", 300, "s"), "Frost_Active", H)
    cal = B.sp(h, "PVB", "HRU_Efficiency_Cal", 1, "", H, "0 / 1")
    est = B.sp(h, "PVR", "HRU_Efficiency_Start", 50, "%", H)
    esp = B.sp(h, "PVR", "HRU_Efficiency_Stop", 45, "%", H)
    ee = B.latch(h, "Eff_En", H, "(A>=B)&!(A<=C)", "A<=C", {"A": P["SC3_Ctrl"], "B": est, "C": esp})
    sok = B.xp(h, "XPB", "!a&!b&!d", {"a": P["bad_TE3"], "b": P["bad_TE6"], "d": P["bad_TE7"]})
    calc = B.xp(h, "XPB", "k&r&e&s&((A-B)>=C)",
                {"k": cal, "r": P["Run"], "e": ee, "s": sok, "A": P["TE7"], "B": P["TE6"],
                 "C": B.ksig(h, "HRU_Eff_Min_dT", 3, "K")}, "Eff_Calc", H)
    raw = B.xp(h, "XPR", "((C-B)*100)/(((A-B)>1)?(A-B):1)", {"A": P["TE7"], "B": P["TE6"], "C": P["TE3"]})
    lim = B.blk(h, "LIMIT", "", [0, 100], [(0, raw)], unit="%")
    eff = B.xp(h, "XPR", "k?A:0", {"k": calc, "A": lim}, "HRU_Efficiency", H, unit="%")
    B.produce("Frost_Active", h.out("Frost_Active", fa, binary=True), "b")
    B.produce("Frost_Cond", h.out("Frost_Cond", fc, binary=True), "b")
    B.produce("HRU_Efficiency", h.out("HRU_Efficiency", eff), "a")
    B.produce("Eff_Calc", h.out("Eff_Calc", calc, binary=True), "b")


def g_pump(B):
    """HFB PumpCtrl: P1 command (cold weather, valve open, freeze group, weekly exercise) and feedback check."""
    p = B.p
    h = p.hfb("PumpCtrl", module="P1")
    ot, tv1, te6, te1 = h.inp("OT"), h.inp("TV1_Ctrl"), h.inp("TE6"), h.inp("TE1")
    fg, fdb = h.inp("Freeze_Group", binary=True), h.inp("P1_Fdb", binary=True)
    run, b6, b1 = h.inp("Run", binary=True), h.inp("bad_TE6", binary=True), h.inp("bad_TE1", binary=True)
    for nm in ("OT", "TV1_Ctrl", "TE6", "TE1", "Freeze_Group", "P1_Fdb", "Run", "bad_TE6", "bad_TE1"):
        B.need(nm, h, nm)
    Q = "P1"
    start = B.sp(h, "PVR", "P1_Start_OT", 9, C, Q, "0 ... 15")
    stop = B.sp(h, "PVR", "P1_Stop_OT", 11, C, Q, "2 ... 20")
    need_ot = B.latch(h, "P1_OT_Need", Q, "(A<=B)&!(A>=C)", "A>=C", {"A": ot, "B": start, "C": stop})
    # the outdoor sensor is not trusted alone: the pump also stays on while the intake air (unit running) or the
    # coil return water is cold, or the sensor that would say so is faulty
    need_air = B.latch(h, "P1_Air_Need", Q, "r&(f|(A<=B))&!(!f&(A>=C))", "!r|(!f&(A>=C))",
                       {"r": run, "f": b6, "A": te6, "B": start, "C": stop})
    w_start = B.sp(h, "PVR", "P1_Start_TE1", 12, C, Q, "5 ... 20")
    w_stop = B.sp(h, "PVR", "P1_Stop_TE1", 14, C, Q, "7 ... 25")
    need_w = B.latch(h, "P1_Water_Need", Q, "(f|(A<=B))&!(!f&(A>=C))", "!f&(A>=C)",
                     {"f": b1, "A": te1, "B": w_start, "C": w_stop})
    wd, hr = B.blk(h, "WDAY"), B.blk(h, "HOUR")
    day = B.sp(h, "PVI", "P1_Ex_Day", 1, "", Q, "WDAY value of Monday, verify")
    ex_in = B.xp(h, "XPB", "(ABS(W-D)<0.5)&(ABS(H-K)<0.5)",
                 {"W": wd, "D": day, "H": hr, "K": B.ksig(h, "P1_Ex_Hour", 10)}, "P1_Ex_Window", Q)
    ex_tr = B.blk(h, "TRIG", "", [1], [(0, ex_in)])
    ex = B.delay(h, ex_tr, 0, B.econ("P1_Ex_Time", 60, "s"), "P1_Ex", Q)
    need = B.xp(h, "XPB", "n|q|w|(V>0)|f|e", {"n": need_ot, "q": need_air, "w": need_w, "V": tv1, "f": fg, "e": ex},
                "P1_Need", Q)
    cmd = B.delay(h, need, 0, B.econ("P1_Off_Delay", 300, "s"), "P1_Run", Q)
    fc_in = B.xp(h, "XPB", "c&!f", {"c": cmd, "f": fdb})
    fc = B.delay(h, fc_in, B.econ("P1_Fdb_Delay", 30, "s"), 0, "P1_Fault_Cond", Q)
    B.produce("P1_Run", h.out("P1_Cmd", cmd, binary=True), "b")
    B.produce("P1_Fault_Cond", h.out("P1_Fault_Cond", fc, binary=True), "b")


def g_outputs(B):
    """Final output selection: public signal Outputs/X and an RO / BO block Outputs/X_OUT per output."""
    p = B.p
    O = "Outputs"
    fhc = B.sp(p, "PVR", "Frost_HRU_Ctrl", 50, "%", "ST", "0 ... 100")
    sig = {}
    for tag, src in (("FZ01_Cmd", "Run"), ("FZ02_Cmd", "Run"), ("TF01_Cmd", "Supply_Released"),
                     ("PF01_Cmd", "Exhaust_Released"), ("P1_Cmd", "P1_Run")):
        sig[tag] = B.blk(p, "DELAY", tag, [0, 0], [(0, src)], module=O)
    for tag, src in (("TF01_Ctrl", "Supply_Speed"), ("PF01_Ctrl", "Exhaust_Speed")):
        sig[tag] = B.blk(p, "LIMIT", tag, [0, 100], [(0, src)], module=O, unit="%")
    fin = B.xp(p, "XPR", "(!s&h)?100:A", {"s": "Season_Mode", "h": "HRU_Hold", "A": "SC3_Seq"}, "SC3_Seq_Final", O,
               unit="%")
    sig["SC3_Ctrl"] = B.xp(p, "XPR", "r?(f?((A<B)?A:B):A):0", {"r": "Run", "f": "Frost_Active", "A": fin, "B": fhc},
                           "SC3_Ctrl", O, unit="%")
    sig["SC3_Cmd"] = B.xp(p, "XPB", "A>1", {"A": sig["SC3_Ctrl"]}, "SC3_Cmd", O)
    sig["TV2_Ctrl"] = B.xp(p, "XPR", "r?A:0", {"r": "Run", "A": "TV2_Seq"}, "TV2_Ctrl", O, unit="%")
    sig["TV1_Ctrl"] = B.xp(p, "XPR", "(r&(A>B))?A:B", {"r": "Run", "A": "TV1_Seq", "B": "Coil_Heat_Ctrl"},
                           "TV1_Ctrl", O, unit="%")
    for tag in ("TF01_Ctrl", "PF01_Ctrl", "SC3_Ctrl", "TV1_Ctrl", "TV2_Ctrl",
                "FZ01_Cmd", "FZ02_Cmd", "TF01_Cmd", "PF01_Cmd", "SC3_Cmd", "P1_Cmd"):
        analog = tag.endswith("_Ctrl")
        B.blk(p, "RO" if analog else "BO", f"{tag}_OUT", ins=[(0, sig[tag])], module=O, public=False,  # public output blocks made the first save on the server fail ("Failed to parse Menta application")
              unit="%" if analog else "")
        B.produce(tag, sig[tag], "a" if analog else "b")
        B.io["outputs"].append({"tag": tag, "kind": "AO" if analog else "DO", "signal": f"{O}/{tag}",
                                "block": f"{O}/{tag}_OUT", "unit": "%" if analog else ""})


SENSOR_TEXT = {"TE00": "Outdoor temperature sensor TE00 faulty"}


def g_alarms(B):
    """The 33 ALARM blocks and the alarm conditions not made elsewhere."""
    p = B.p
    A = "Alarms"
    stopped = "Unit stopped"
    for name, src, text in (
            ("Freeze_Alm", "Freeze_Latch", "Freeze protection tripped: coil return water or supply air too cold. "),
            ("Fire_Alm", "Fire_Latch", "Fire alarm from the fire panel. "),
            ("Stop_Alm", "Stop_Latch", "Emergency stop button pressed. "),
            ("P1_Alm", "P1_Latch", "Heating coil pump P1 not running. "),
            ("HN_Pres_Alm", "HN_Pres_Latch", "Heat supply water pressure alarm. "),
            ("HN_Temp_Alm", "HN_Temp_Latch", "Heat supply water temperature alarm. "),
            ("Supply_Fire_Alm", "Supply_Fire_Latch", "Supply air temperature at fire limit. "),
            ("Exhaust_Fire_Alm", "Exhaust_Fire_Latch", "Extract air temperature at fire limit. ")):
        B.alarm(name, src, text + stopped, 0, "A")
    for t in TEMPS:
        if t.startswith("TE10"):
            text = f"Room temperature sensor TE10.{t[-1]} faulty"
        else:
            text = SENSOR_TEXT.get(t, f"Temperature sensor {t} faulty")
        B.alarm(f"{t}_Alm", f"bad_{t}", text, 180, "B")
    dev = B.sp(p, "PVR", "Supply_Temp_Dev", 5, "K", A)
    stc = B.xp(p, "XPB", "r&(ABS(A-B)>C)", {"r": "Supply_Released", "A": "TE2", "B": "Active_SP", "C": dev},
               "Supply_Temp_Cond", A)
    B.alarm("Supply_Temp_Alm", stc, "Supply air temperature deviates from setpoint", 300, "B")
    B.alarm("Supply_Pres_Alm", "Supply_Pres_Cond", "Supply duct pressure deviates from setpoint", 900, "B")
    B.alarm("Exhaust_Pres_Alm", "Exhaust_Pres_Cond", "Extract duct pressure deviates from setpoint", 900, "B")
    B.alarm("TF01_Alm", "Supply_Fdb_Cond", "Supply fan TF01 commanded but not running", 900, "B")
    B.alarm("PF01_Alm", "Exhaust_Fdb_Cond", "Extract fan PF01 commanded but not running", 900, "B")
    hf = B.xp(p, "XPB", "!a", {"a": "SC3_Fault"}, "HRU_Fault_Cond", A)
    B.alarm("HRU_Alm", hf, "Heat recovery drive SC3 fault", 180, "B")
    B.alarm("HRU_Frost_Alm", "Frost_Cond", "Heat recovery icing: rotor speed limited", 180, "B")
    tsp = B.sp(p, "PVR", "HRU_Temp_SP", 5, C, A)
    esp = B.sp(p, "PVR", "HRU_Efficiency_SP", 40, "%", A)
    csp = B.sp(p, "PVR", "HRU_Ctrl_SP", 90, "%", A)
    ec = B.xp(p, "XPB", "k&!g&(A<=B)&(C<=D)&(E>=F)",
              {"k": "Eff_Calc", "g": "Frost_Active", "A": "TE6", "B": tsp, "C": "HRU_Efficiency", "D": esp,
               "E": "SC3_Ctrl", "F": csp}, "HRU_Eff_Cond", A)
    B.alarm("HRU_Efficiency_Alm", ec, "Heat recovery efficiency low", 300, "B")
    hr = B.xp(p, "XPB", "r&!a&!b&(C>=D)&((F-E)<G)",
              {"r": "Run", "a": "bad_TE3", "b": "bad_TE4", "C": "TV1_Ctrl", "D": B.ksig(p, "HeatR_Valve_SP", 30, "%"),
               "E": "TE3", "F": "TE4", "G": B.ksig(p, "HeatR_dT", 1, "K")}, "HeatR_Cond", A)
    B.alarm("HeatR_Alm", hr, "Heating coil gives no heat although the valve is open", 300, "B")
    ce = B.xp(p, "XPB", "r&s&!a&!b", {"r": "Run", "s": "Season_Mode", "a": "bad_TE4", "b": "bad_TE5"})
    cr = B.xp(p, "XPB", "k&(C>=D)&((E-F)<G)",
              {"k": ce, "C": "TV2_Ctrl", "D": B.ksig(p, "CoolR_Valve_SP", 30, "%"), "E": "TE4", "F": "TE5",
               "G": B.ksig(p, "CoolR_dT", 1, "K")}, "CoolR_Cond", A)
    B.alarm("CoolR_Alm", cr, "Cooling coil gives no cooling although the valve is open", 300, "B")
    B.alarm("PDE3_Alm", "PDE3_Cond", "Supply filter stage 1 dirty", 300, "C")
    B.alarm("PDE1_Alm", "PDE1_Cond", "Supply filter stage 2 dirty", 300, "C")
    B.alarm("PDE2_Alm", "PDE2_Cond", "Extract filter dirty", 300, "C")


GROUPS = {"Inputs": g_inputs, "SensorCheck": g_sensorcheck, "DayMean": g_daymean, "Modes": g_modes,
          "Latches": g_latches, "Fan": g_fan, "Filters": g_filters, "TempSeq": g_tempseq, "CoilProtect": g_coil,
          "HruFrostEff": g_hru, "PumpCtrl": g_pump, "Outputs": g_outputs, "Alarms": g_alarms}

# meaning of the computed public signals, for io.json "states" (anything not listed gets its block type)
MEANING = {
    "Inputs/OT": "outdoor temperature in use (TE00, or OT_Fault_Value while TE00 is faulty)",
    "Inputs/OT_OK": "TE00 healthy", "Inputs/Room_Avg": "mean of the healthy room sensors",
    "Inputs/Room_OK": "at least one room sensor healthy", "Inputs/Room_N": "number of healthy room sensors",
    "Inputs/OT_Day_Mean": "mean outdoor temperature of the previous day",
    "Inputs/Reset_Pulse": "one-cycle alarm reset pulse", "Inputs/Supply_Flow": "supply air flow m3/s",
    "Inputs/Exhaust_Flow": "extract air flow m3/s",
    "Operation/Season_Mode": "1 cooling season (summer sequence), 0 heating season",
    "Operation/Auto_Season": "season from the daily mean (before the selector)",
    "Operation/HS10_Ext": "extended run from HS10 active", "Operation/Operation": "normal operation",
    "Operation/Night_Cooling": "night cooling running", "Operation/Night_Heating": "night heating running",
    "Operation/Run": "unit running", "Operation/Run_Mode": "0 stopped, 1 normal, 2 night cooling, 3 night heating, "
                                                          "4 stopped by critical alarm",
    "Alarms/Critical_Alarm": "any critical latch set", "Alarms/Freeze_Group": "freeze latch or pump latch set",
    "FAN/Supply_Released": "supply fan released (= TF01_Cmd)", "FAN/Exhaust_Released": "extract fan released",
    "FAN/Supply_Pressure_SP": "supply duct pressure setpoint in use",
    "FAN/Exhaust_Pressure_SP": "extract duct pressure setpoint in use", "FAN/Low_Speed_Cmd": "low speed mode active",
    "ST/Active_SP": "supply temperature setpoint of the active sequence", "ST/H_Seq": "heating sequence signal H",
    "ST/C_Seq": "cooling sequence signal C", "ST/Cool_Recovery": "cooling recovery by the rotor",
    "ST/PreHeat_Pulse": "start-up pre-heat pulse", "ST/HRU_Hold": "rotor held at 100 % after start",
    "ST/Coil_Heat_Ctrl": "coil return water control output", "ST/Coil_En": "coil return water control enabled",
    "HRU/Frost_Active": "rotor frost limit active", "HRU/Frost_Cond": "rotor icing condition",
    "HRU/HRU_Efficiency": "temperature efficiency %", "HRU/Eff_Calc": "efficiency being calculated",
    "P1/P1_Run": "pump command before the output", "P1/P1_Fault_Cond": "pump commanded, no feedback (delayed)",
    "P1/P1_Ex": "weekly exercise running",
}


def build(only=None):
    B = Builder(only)
    for name, fn in GROUPS.items():
        if not only or name in only:
            fn(B)
    B.finish()
    skip = {"PVR", "PVB", "PVI", "RI", "BI", "RO", "BO", "ALARM", "DELB", "HFB", "HFAI", "HFDI", "HFAO", "HFDO"}
    for b in B.p.all_blocks():
        if b.public and b.name and b.typ not in skip and b.module != "Test":
            path = f"{b.module}/{b.name}"
            kind = {"XPB": "binary", "SR": "binary", "DELAY": "binary", "TRIG": "binary", "XPI": "integer"}.get(
                b.typ, "analog")
            B.io["states"].append({"path": path, "kind": kind, "block": b.typ,
                                   "meaning": MEANING.get(path, b.typ)})
    return B


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma separated group names: write AHU01_part.aut with just those")
    ap.add_argument("--list", action="store_true", help="print the group names")
    ap.add_argument("--out", default=HERE, help="output directory")
    a = ap.parse_args()
    if a.list:
        print(" ".join(GROUPS)); return 0
    only = None
    if a.only:
        only = [g.strip() for g in a.only.split(",") if g.strip()]
        bad = [g for g in only if g not in GROUPS]
        if bad:
            print(f"unknown group(s) {bad}; groups: {' '.join(GROUPS)}", file=sys.stderr); return 2
    B = build(only)
    p = B.p
    chk = p.check()
    fn = os.path.join(a.out, "AHU01_part.aut" if only else "AHU01.aut")
    p.save(fn)
    ov = p.all_overlaps()
    st = p.stats()
    st["alarms"] = sum(1 for b in p.all_blocks() if b.typ == "ALARM")
    st["public_constants"] = sum(1 for c in p.consts if c[3])
    print(f"{os.path.basename(fn)}: {json.dumps(st)}")
    if only:
        print(f"groups: {', '.join(only)}; test values in module Test: {', '.join(sorted(B.test)) or 'none'}")
    else:
        json.dump(p.expected(), open(os.path.join(a.out, "expected.json"), "w"), indent=1)
        json.dump(B.io, open(os.path.join(a.out, "io.json"), "w"), indent=1, ensure_ascii=False)
    print(f"check: {chk if chk else 'nothing found'}; wire overlaps: {len(ov)}")
    return 1 if chk or ov else 0


if __name__ == "__main__":
    sys.exit(main())
