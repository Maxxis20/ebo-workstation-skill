#!/usr/bin/env python3
"""make_program.py - FanSeq.aut: a start / stop step chain for one fan with a shut-off damper, as one EBO Function
Block program, with the plant simulated in the same program so that it runs without I/O.

    python3 make_program.py        -> FanSeq.aut, io.json

The step table is in steps.py. How the chain works (module Seq), each cycle, from what the cycle before left:
  P      step of the cycle before (DELI)          T     time in the step, s
  RQ1/2  requirement 1 / 2 of step P              N     number of requirements of step P
  FBAD   first requirement not met (N + 1 = all met)
  RQ_AT  requirement being checked now: moves up one per cycle while met, falls back at once to FBAD
  SUP    supervision time: counts while a requirement is not met; in the run step it restarts when all are met
  FIRE   SUP reached the step's supervision time -> sequence alarm (class B, held until Reset), the step and the
         requirement are kept in AL_STEP / AL_REQ, a start or run step goes to the first stop step
  SETTLE every requirement checked and met; the step moves on when this has lasted the settle time
  Trip   emergency stop (class A): step 0 at once, the commands drop in the same cycle (interlock), held until Reset
  Step durations D1 ... D5 are kept when a step is left and cleared at a new start.

Inputs (module Inputs) are RI blocks bound to server values in folder Cmd (written by the graphic, or by MQTT in the
tests): Mode (0 Off, 1 On, 2 Auto), Auto_Demand (stands in for a time schedule), E_Stop, Reset (a counter: every
change is one reset), Fault_Damper (damper does not open), Fault_Fan (fan feedback lost).
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from aut import Program, expr_inputs
from steps import STEPS, RUN_STEP, FIRST_STOP, RUNON_S, N_REQ

CYCLE_MS = 500
p = Program("FanSeq", cycle_ms=CYCLE_MS)
io = {"inputs": [], "public": []}


def X(typ, expr, ins, name="", module="", public=None, unit="", desc=""):
    """Expression block; ins = {letter: source}."""
    letters = expr_inputs(expr)
    if sorted(letters) != sorted(ins):
        raise ValueError(f"{expr!r}: letters {letters}, given {sorted(ins)}")
    if len(expr) > 60 or len(letters) > 8:
        raise ValueError(f"{expr!r}: too long ({len(expr)} characters, {len(letters)} inputs)")
    if public is None:
        public = bool(name)
    b = p.block(typ, name, [expr], unit=unit, public=public, module=module, desc=desc)
    for k, s in ins.items():
        p.wire(s, b, k)
    if public and name:
        io["public"].append(f"{module}/{name}")
    return b


def B(typ, name, params, src=None, module="", public=None, unit="", desc=""):
    if public is None:
        public = bool(name)
    b = p.block(typ, name, params, unit=unit, public=public, module=module, desc=desc)
    if src is not None:
        p.wire(src, b)
    if public and name:
        io["public"].append(f"{module}/{name}")
    return b


def nested(by_step, default=0):
    """P=1?v1:(P=2?v2:(...:default)) as an expression on letter A."""
    e = str(default)
    for k, v in reversed(by_step):
        e = f"(A={k}?{v:g}:{e})"
    return e[1:-1]


# ---- inputs --------------------------------------------------------------------------------------------------
I = "Inputs"
ins = {}
for n, d in (("Mode", "0 Off, 1 On, 2 Auto"), ("Auto_Demand", "demand in Auto (time schedule stand-in)"),
             ("E_Stop", "emergency stop pressed"), ("Reset", "counter: each change resets"),
             ("Fault_Damper", "test: damper does not open"), ("Fault_Fan", "test: fan feedback lost")):
    ins[n] = p.block("RI", n, desc=d, module=I, public=True)
    io["inputs"].append({"tag": n, "module": I, "desc": d})
tc = B("TCYC", "", [], module=I, public=False)
rs_prev = B("DELR", "", [0], ins["Reset"], module=I, public=False)
rst = X("XPB", "ABS(A-B)>0.5", {"A": ins["Reset"], "B": rs_prev}, "Reset_Pulse", I)
es = X("XPB", "A>0.5", {"A": ins["E_Stop"]}, "E_Stop_On", I)
auto = X("XPB", "A>0.5", {"A": ins["Auto_Demand"]}, public=False, module=I)
f_dmp = X("XPB", "A>0.5", {"A": ins["Fault_Damper"]}, public=False, module=I)
f_fan = X("XPB", "A>0.5", {"A": ins["Fault_Fan"]}, public=False, module=I)

# ---- state of the cycle before (the loop is closed through these one-cycle delays) ----------------------------
S = "Seq"
P = B("DELI", "Prev_Step", [0], module=S, public=False)
Tp = B("DELR", "", [0], module=S, public=False)
Sp = B("DELR", "", [0], module=S, public=False)
Wp = B("DELR", "", [0], module=S, public=False)
Qp = B("DELI", "", [0], module=S, public=False)
Ap = B("DELB", "", [0], module=S, public=False)
ALSp = B("DELI", "", [0], module=S, public=False)
ALRp = B("DELI", "", [0], module=S, public=False)
TRp = B("DELB", "", [0], module=S, public=False)
Dp = [B("DELR", "", [0], module=S, public=False) for _ in STEPS]

# ---- trip and demand -----------------------------------------------------------------------------------------
trip = X("XPB", "p|(q&!r)", {"p": es, "q": TRp, "r": rst}, "Trip", S, desc="class A: emergency stop, held until Reset")
demand = X("XPB", "!t&((A=1)|((A=2)&p))", {"A": ins["Mode"], "p": auto, "t": trip}, "Demand", S)

# ---- commands (from the step of the cycle before; the trip drops them in the same cycle) ----------------------
O = "Outputs"
dmp_cmd = X("XPB", f"!t&(((A>0)&(A<5))|((A=5)&(B<{RUNON_S})))", {"A": P, "B": Tp, "t": trip}, "Damper_Cmd", O)
fan_cmd = X("XPB", "!t&((A=2)|(A=3))", {"A": P, "t": trip}, "Fan_Cmd", O)

# ---- plant simulation ----------------------------------------------------------------------------------------
M = "Sim"
d_tgt = X("XPR", "p&!q?100:0", {"p": dmp_cmd, "q": f_dmp}, public=False, module=M)
d_pos = B("RAMP", "Damper_Pos", [25], d_tgt, module=M, unit="%", desc="damper position, 4 s stroke")
d_open = X("XPB", "A>=95", {"A": d_pos}, "Damper_Open", M, desc="open end switch")
d_closed = X("XPB", "A<=5", {"A": d_pos}, "Damper_Closed", M, desc="closed end switch")
f_dly = B("DELAY", "", [2, 2], fan_cmd, module=M, public=False)
fan_fdb = X("XPB", "p&!q", {"p": f_dly, "q": f_fan}, "Fan_Fdb", M, desc="fan running feedback")
p_tgt = X("XPR", "p?150:0", {"p": fan_fdb}, public=False, module=M)
pres = B("RAMP", "Duct_Pressure", [40], p_tgt, module=M, unit="Pa", desc="duct pressure, 40 Pa/s")

# ---- requirements of every step -------------------------------------------------------------------------------
R = "Req"
fan_off = X("XPB", "!p", {"p": fan_fdb}, public=False, module=R)
p50 = X("XPB", "A>=50", {"A": pres}, public=False, module=R)
p20 = X("XPB", "A<20", {"A": pres}, public=False, module=R)
runon = X("XPB", f"A>={RUNON_S}", {"A": Tp}, public=False, module=R)
REQ = {1: [d_open], 2: [fan_fdb, p50], 3: [fan_fdb, d_open], 4: [fan_off, p20], 5: [runon, d_closed]}
assert [len(REQ[s[0]]) for s in STEPS] == [len(s[3]) for s in STEPS]
rq = []
for j in range(N_REQ):
    terms, srcs = [], {"A": P}
    for k, letter in zip(sorted(REQ), "pqrst"):
        if j < len(REQ[k]):
            terms.append(f"((A={k})&{letter})"); srcs[letter] = REQ[k][j]
    rq.append(X("XPB", "|".join(terms), srcs, f"RQ{j + 1}", S, desc=f"requirement {j + 1} of the step"))

# ---- the chain -----------------------------------------------------------------------------------------------
n = X("XPI", nested([(s[0], len(s[3])) for s in STEPS]), {"A": P}, "N_Req", S)
tmax = X("XPR", nested([(s[0], s[5]) for s in STEPS]), {"A": P}, "T_Max", S, unit="s")
settle = X("XPR", nested([(s[0], s[4]) for s in STEPS]), {"A": P}, "T_Settle", S, unit="s")
fbad = X("XPI", "!p?1:((A>1)&!q?2:A+1)", {"A": n, "p": rq[0], "q": rq[1]}, "FBAD", S,
         desc="first requirement not met; N + 1 = all met")
q = X("XPI", "(A+1)<B?A+1:B", {"A": Qp, "B": fbad}, "RQ_AT", S, desc="requirement checked now")
t = X("XPR", "A+B", {"A": Tp, "B": tc}, public=False, module=S)
sup = X("XPR", f"(B<=C)?A+D:((E={RUN_STEP})?0:A)", {"A": Sp, "B": fbad, "C": n, "D": tc, "E": P}, public=False,
        module=S)
fire = X("XPB", "(E>0)&(A>=F)&!p", {"A": sup, "E": P, "F": tmax, "p": Ap}, public=False, module=S)
alarm = X("XPB", "(p|q)&!r", {"p": Ap, "q": fire, "r": rst}, "Seq_Alarm", S, desc="class B, held until Reset")
als = X("XPI", "p?B:A", {"A": ALSp, "B": P, "p": fire}, "AL_Step", S, desc="step that gave the sequence alarm")
alr = X("XPI", "p?B:A", {"A": ALRp, "B": fbad, "p": fire}, "AL_Req", S, desc="requirement not met in time")
w = X("XPR", f"(B>C)&(C>0)&(E!={RUN_STEP})?A+D:0", {"A": Wp, "B": q, "C": n, "D": tc, "E": P}, public=False,
      module=S)
adv = X("XPB", "A>=B", {"A": w, "B": settle}, public=False, module=S)
adv2 = X("XPB", "p&(A>0)", {"A": w, "p": adv}, public=False, module=S)
stop = X("XPB", f"(A>0)&(A<{FIRST_STOP})&(!p|q)", {"A": P, "p": demand, "q": fire}, public=False, module=S)
last = STEPS[-1][0]
step = X("XPI", f"t?0:(A=0?(p&!q?1:0):(r?{FIRST_STOP}:(s?(A={last}?0:A+1):A)))",
         {"A": P, "p": demand, "q": alarm, "r": stop, "s": adv2, "t": trip}, "Step", S, desc="step now, 0 = idle")
chg = X("XPB", "A!=B", {"A": step, "B": P}, public=False, module=S)
start = X("XPB", "(A=0)&(B=1)", {"A": P, "B": step}, public=False, module=S)

# store for the next cycle: a step change restarts the step's timers and the check
p.wire(step, P)
T_s = X("XPR", "p?0:A", {"A": t, "p": chg}, "Step_Time", S, unit="s", desc="time in the step")
p.wire(T_s, Tp)
S_s = X("XPR", "p?0:A", {"A": sup, "p": chg}, "Sup_Time", S, unit="s", desc="supervision time running")
p.wire(S_s, Sp)
W_s = X("XPR", "p?0:A", {"A": w, "p": chg}, "Settle_Time", S, unit="s")
p.wire(W_s, Wp)
Q_s = X("XPI", "p?0:A", {"A": q, "p": chg}, public=False, module=S)
p.wire(Q_s, Qp)
p.wire(alarm, Ap); p.wire(als, ALSp); p.wire(alr, ALRp); p.wire(trip, TRp)
D = []
for (k, *_), dp in zip(STEPS, Dp):
    d = X("XPR", f"q?0:((p&(B={k}))?A:C)", {"A": t, "B": P, "C": dp, "p": chg, "q": start}, f"D{k}", S, unit="s",
          desc=f"duration of step {k} in this run")
    p.wire(d, dp); D.append(d)

# ---- what the graphic shows ----------------------------------------------------------------------------------
H = "Hmi"
for (k, name, _does, reqs, _st, tm), d in zip(STEPS, D):
    X("XPI", f"(p&(A={k}))?3:((B={k})?1:(C>0?2:0))", {"A": als, "B": step, "C": d, "p": alarm}, f"ST{k}", H,
      desc="0 waiting, 1 active, 2 done, 3 caused the alarm")
    X("XPR", f"(A={k})?B:(C>0?C:{tm:g})", {"A": step, "B": T_s, "C": d}, f"SHOW{k}", H, unit="s",
      desc="active: time in step; done: duration; waiting: supervision time")
    for j in range(1, len(reqs) + 1):
        X("XPI", f"(p&(A={k})&(B={j}))?4:((C={k})?(D>{j}?1:(D={j}?2:3)):(E>0?1:0))",
          {"A": als, "B": alr, "C": P, "D": q, "E": d, "p": alarm}, f"RS{k}_{j}", H,
          desc="0 -, 1 OK, 2 checking, 3 next, 4 not met in time")
X("XPI", f"t?4:(p?5:(A={RUN_STEP}?2:(A>{RUN_STEP}?3:(A>0?1:0))))", {"A": step, "p": alarm, "t": trip}, "Unit_State",
  H, desc="0 stopped, 1 starting, 2 running, 3 stopping, 4 trip, 5 sequence alarm")
X("XPR", "B>0?A/B*100:0", {"A": S_s, "B": tmax}, "Sup_Pct", H, unit="%")

# ---- alarms --------------------------------------------------------------------------------------------------
A_ = "Alarms"
p.alarm("Trip_Alarm", trip, "Emergency stop: fan sequence tripped, fan and damper stopped at once", priority=1,
        module=A_)
for k, name, _does, reqs, _st, tm in STEPS:
    for j, rtext in enumerate(reqs, 1):
        c = X("XPB", f"p&(A={k})&(B={j})", {"A": als, "B": alr, "p": alarm}, public=False, module=A_)
        p.alarm(f"Seq_S{k}_R{j}", c, f"Sequence alarm: step {k} {name}, requirement {j} ({rtext}) not met in "
                f"{tm:g} s", priority=2, module=A_)

bad = p.check()
if bad:
    sys.exit("\n".join(bad))
p.layout()
p.save(os.path.join(HERE, "FanSeq.aut"))
json.dump(io, open(os.path.join(HERE, "io.json"), "w"), indent=1)
print("FanSeq.aut:", p.stats())
