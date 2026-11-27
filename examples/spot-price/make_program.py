#!/usr/bin/env python3
"""make_program.py - Spot.aut: a load run by the day-ahead electricity price, as one EBO Function Block program.

    python3 make_program.py        -> Spot.aut, io.json

Prices come from a spot price bridge over MQTT into server values (folder Spot, make_objects.py); the operator
settings are server values in folder Set. Two ways to choose the hours, setting Set/Mode:

  0  the N cheapest hours of today (Set/N_Cheap): on while the running hour's rank <= N
  1  the cheapest N consecutive hours (Set/N_Block, 1..12) among the upcoming known hours: the bridge says in how
     many hours that block starts (spot.blk<N>), and the program HOLDS it: the plan (start in Plan_Wait hours,
     Plan_Left hours long) counts down with the clock and is only planned again when it has run, or, while it is
     still waiting, when more hours become known (tomorrow's prices arrive) or N changes. A plan that is made again
     every hour could postpone the load for ever.

Set/Res chooses the price resolution: 0 hourly, 1 15 minutes. It sets the price the limits are checked against
(the hour's or the quarter's) and what the graph shows (36 hours, or 36 quarters = 9 hours). The choice of hours
(rank, the block) stays hourly: the bridge ranks hours, and ranking 96 quarters is not practical in this program.

Set/Unit_MWh shows the prices in EUR/MWh instead of c/kWh (Hmi/Disp_*); inside, and in the settings, c/kWh.
All prices are without VAT (VAT 0 %), as the bridge serves them.

Over both: at or below Set/Force_Below the load runs (cheap or negative price), above Set/Block_Above it does not.
Set/Ctl_On = 0 switches price control off.

  Stale      the bridge's beat (one step every 10 s) has not changed for 60 s: the bridge is stopped
  No_Price   valid = 0 or Stale: no usable price
  Reason     0 price control off -> normal; 1 chosen hour -> on; 2 not chosen -> off; 3 above the block limit -> off;
             4 at or below the force limit -> on; 5 no price data -> normal operation and an alarm
  Load_Cmd   Normal_Demand in reasons 0 and 5, else on in 1 and 4, off in 2 and 3
  Alarms     Price_Invalid (valid = 0) and Bridge_Stopped (beat still), priority 2, only while price control is on
  Hmi/U<k>   class of upcoming hour k for the graph: 0 normal, 1 chosen, 2 above the block limit, 3 at or below the
             force limit, 4 not known yet. Chosen in mode 0 = at or below today's N-th cheapest price
             (Hmi/N_Price); in mode 1 = inside the held block.

"Normal operation" is what the load does without prices (thermostat, time schedule): Set/Normal_Demand stands in.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from aut import Program, expr_inputs

STALE_S = 60
HORIZON = 36            # upcoming hours the program looks at and the graph shows (the bridge gives up to 48)
NMAX = 12               # longest consecutive block (the bridge gives blk1 .. blk12)
p = Program("Spot", cycle_ms=1000)
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


def RI(module, name, source, desc="", unit=""):
    """Input bound to a server value: source = 'Spot/<key>' or 'Set/<name>' below the example folder."""
    b = p.block("RI", name, desc=desc, unit=unit, module=module, public=True)
    io["inputs"].append({"module": module, "tag": name, "source": source})
    return b


def DEL(module, typ="DELR"):
    return p.block(typ, "", [0], module=module)


# ---- inputs: prices from the bridge (folder Spot), settings from the operator (folder Set) ------------------
I, D = "Inputs", "Prices"
valid = RI(I, "Valid", "Spot/valid", "1 = prices usable (bridge)")
beat = RI(I, "Beat", "Spot/beat", "counts up every 10 s while the bridge runs")
hour = RI(I, "Hour", "Spot/hour", "running local hour 0..23")
price = RI(I, "Price", "Spot/now", "price of the running hour", "c/kWh")
rank = RI(I, "Rank", "Spot/rank", "1 = cheapest hour of today")
known = RI(I, "Known", "Spot/known", "upcoming hours with a price, from the running one")
ctl = RI(I, "Ctl_On", "Set/Ctl_On", "operator: price control on")
mode = RI(I, "Mode", "Set/Mode", "operator: 0 N cheapest hours, 1 cheapest N consecutive hours")
n_ch = RI(I, "N_Cheap", "Set/N_Cheap", "operator: N for the N cheapest hours of today")
n_bl = RI(I, "N_Block", "Set/N_Block", f"operator: length of the consecutive block, 1..{NMAX} h")
blk = RI(I, "Block_Above", "Set/Block_Above", "operator: off above this price", "c/kWh")
frc = RI(I, "Force_Below", "Set/Force_Below", "operator: on at or below this price", "c/kWh")
res = RI(I, "Res", "Set/Res", "operator: 0 hourly prices, 1 15 minute prices")
now15 = RI(I, "Price15", "Spot/now15", "price of the running quarter", "c/kWh")
quarter = RI(I, "Quarter", "Spot/quarter", "running quarter of the day 0..95")
known15 = RI(I, "Known15", "Spot/known15", "upcoming quarters with a price, from the running one")
unit_mwh = RI(I, "Unit_MWh", "Set/Unit_MWh", "operator: show prices in EUR/MWh instead of c/kWh")
avg = RI(I, "Day_Avg", "Spot/avg", "average of today", "c/kWh")
mn = RI(I, "Day_Min", "Spot/min", "lowest hour of today", "c/kWh")
mx = RI(I, "Day_Max", "Spot/max", "dearest hour of today", "c/kWh")
norm = RI(I, "Normal_Demand", "Set/Normal_Demand", "demand without prices (thermostat, schedule)")
H = [RI(D, f"H{k}", f"Spot/h{k}", f"today, hour {k}", "c/kWh") for k in range(24)]
R = [RI(D, f"R{k}", f"Spot/r{k}", f"rank of today, hour {k}") for k in range(24)]
U = [RI(D, f"U{k}", f"Spot/u{k}", f"upcoming hour {k} (0 = running)", "c/kWh") for k in range(HORIZON)]
Q = [RI(D, f"Q{k}", f"Spot/q{k}", f"upcoming quarter {k} (0 = running)", "c/kWh") for k in range(HORIZON)]

# ---- is the bridge alive ---------------------------------------------------------------------------------------
C = "Ctl"
tc = p.block("TCYC", "", [], module=C)
b_prev = DEL(C); p.wire(beat, b_prev)
age_p = DEL(C)
age = X("XPR", "ABS(A-B)>0.5?0:C+D", {"A": beat, "B": b_prev, "C": age_p, "D": tc}, "Beat_Age", C, unit="s",
        desc="seconds since the beat last changed")
p.wire(age, age_p)
stale = X("XPB", f"A>={STALE_S}", {"A": age}, "Stale", C, desc=f"beat still for {STALE_S} s: bridge stopped")
noprice = X("XPB", "(A<0.5)|p", {"A": valid, "p": stale}, "No_Price", C)
on = X("XPB", "A>0.5", {"A": ctl}, public=False, module=C)
q15 = X("XPB", "A>0.5", {"A": res}, "Res15", C, desc="15 minute prices chosen")
p_used = X("XPR", "p?A:B", {"p": q15, "A": now15, "B": price}, "Price_Used", C, unit="c/kWh",
           desc="the price the limits are checked against: of the quarter or of the hour")
blockmode = X("XPB", "(A>0.5)&p&!q", {"A": mode, "p": on, "q": noprice}, "Block_Mode", C)
nb = X("XPR", f"A<1?1:(A>{NMAX}?{NMAX}:A)", {"A": n_bl}, "N_Block_Used", C, desc=f"N_Block limited to 1..{NMAX}")

# ---- cheapest consecutive block: the bridge says where it starts (blk<N>), the program picks N ----------------
W = "Block"
BLK = [RI(W, f"Blk{n}", f"Spot/blk{n}", f"hours until the cheapest {n} h in a row start, -1 = unknown", "h")
       for n in range(1, NMAX + 1)]
m1 = X("XPI", "A=1?B:(A=2?C:(A=3?D:(A=4?E:(A=5?F:G))))",
       {"A": nb, "B": BLK[0], "C": BLK[1], "D": BLK[2], "E": BLK[3], "F": BLK[4], "G": BLK[5]}, module=W, public=False)
m2 = X("XPI", "A=7?B:(A=8?C:(A=9?D:(A=10?E:(A=11?F:G))))",
       {"A": nb, "B": BLK[6], "C": BLK[7], "D": BLK[8], "E": BLK[9], "F": BLK[10], "G": BLK[11]}, module=W,
       public=False)
best_in = X("XPI", "A<=6?B:C", {"A": nb, "B": m1, "C": m2}, "Best_In", W,
            desc="hours until the cheapest block starts (0 = now, -1 = not enough hours known)")
best_ok = X("XPB", "A>=0", {"A": best_in}, "Best_OK", W)

# ---- the held plan --------------------------------------------------------------------------------------------
P_ = "Plan"
h_prev = DEL(P_); p.wire(hour, h_prev)
tick = X("XPB", "ABS(A-B)>0.5", {"A": hour, "B": h_prev}, "Hour_Tick", P_, desc="the hour changed")
w_p, l_p, ka_p, na_p = DEL(P_), DEL(P_), DEL(P_), DEL(P_)
pl_p = DEL(P_, "DELB")
replan = X("XPB", "p&(!q|((A>0)&((B>C+1)|(ABS(D-E)>0.5))))",
           {"p": blockmode, "q": pl_p, "A": w_p, "B": known, "C": ka_p, "D": nb, "E": na_p}, "Replan", P_,
           desc="no plan, or still waiting and 2+ more hours known (not the same-hour jitter of known) or N changed")
wait = X("XPR", "r?A:(p&(B>0)?B-1:B)", {"r": replan, "A": best_in, "p": tick, "B": w_p}, "Plan_Wait", P_,
         unit="h", desc="hours until the planned block starts")
left = X("XPR", "r?A:(p&(B<0.5)&(C>0)?C-1:C)", {"r": replan, "A": nb, "p": tick, "B": w_p, "C": l_p}, "Plan_Left",
         P_, unit="h", desc="hours of the block still to run")
ka = X("XPR", "r?A:(p?B-1:B)", {"r": replan, "A": known, "p": tick, "B": ka_p}, "Known_At_Plan", P_)
na = X("XPR", "r?A:B", {"r": replan, "A": nb, "B": na_p}, public=False, module=P_)
planned = X("XPB", "r?q:(s&t&!(p&(A<0.5)&(B<1.5)))",
            {"r": replan, "q": best_ok, "s": pl_p, "t": blockmode, "p": tick, "A": w_p, "B": l_p}, "Planned", P_)
for src, dst in ((wait, w_p), (left, l_p), (ka, ka_p), (na, na_p), (planned, pl_p)):
    p.wire(src, dst)
inblock = X("XPB", "p&(A<0.5)&(B>0.5)", {"p": planned, "A": wait, "B": left}, "In_Block", P_,
            desc="the held block is running now")

# ---- the decision ----------------------------------------------------------------------------------------------
chosen = X("XPB", "(A>0.5)?p:(B<=C)", {"A": mode, "p": inblock, "B": rank, "C": n_ch}, "Chosen", C,
           desc="this hour is one of the chosen ones")
reason = X("XPI", "!p?0:(q?5:(A<=B?4:(A>C?3:(r?1:2))))",
           {"p": on, "q": noprice, "A": p_used, "B": frc, "C": blk, "r": chosen}, "Reason", C,
           desc="0 off, 1 chosen, 2 not chosen, 3 blocked, 4 forced, 5 no price")
X("XPB", "(A=0)|(A=5)?B>0.5:(A=1)|(A=4)", {"A": reason, "B": norm}, "Load_Cmd", C, desc="the load runs")

# ---- alarms (only while price control is on) -------------------------------------------------------------------
A_ = "Alarms"
inv = X("XPB", "p&(A<0.5)", {"A": valid, "p": on}, public=False, module=A_)
stp = X("XPB", "p&q", {"p": on, "q": stale}, public=False, module=A_)
p.alarm("Price_Invalid", inv, "Spot price: no valid prices from the bridge, load in normal operation", priority=2,
        module=A_)
p.alarm("Bridge_Stopped", stp, f"Spot price: bridge stopped (no beat for {STALE_S} s), load in normal operation",
        priority=2, module=A_)

# ---- for the graph: today's N-th cheapest price, class of every upcoming hour ------------------------------------
M = "Hmi"
thr = X("XPR", "A<=B?C:-999", {"A": R[0], "B": n_ch, "C": H[0]}, module=M, public=False)
for k in range(1, 24):
    thr = X("XPR", "(A<=B)&(C>D)?C:D", {"A": R[k], "B": n_ch, "C": H[k], "D": thr}, module=M, public=(k == 23),
            **({"name": "N_Price", "unit": "c/kWh"} if k == 23 else {}))
qoff = X("XPR", "A-B*4", {"A": quarter, "B": hour}, module=M, public=False)     # quarter within the hour
kn = X("XPR", "p?A:B", {"p": q15, "A": known15, "B": known}, "Known_Used", M)
for k in range(HORIZON):
    gk = X("XPR", "p?A:B", {"p": q15, "A": Q[k], "B": U[k]}, f"G{k}", M, unit="c/kWh",
           desc=f"graph bar {k}: upcoming quarter or hour")
    inp = X("XPB", f"r?p&(A*4-C<={k})&((A+B)*4-C>{k}):p&(A<={k})&(A+B>{k})",
            {"p": planned, "A": wait, "B": left, "C": qoff, "r": q15}, module=M, public=False)
    X("XPI", f"{k}>=A?4:(B<=C?3:(B>D?2:((q?p:(B<=E))?1:0)))",
      {"A": kn, "B": gk, "C": frc, "D": blk, "E": thr, "p": inp, "q": blockmode}, f"U{k}", M)
    if k % 3 == 0:                                   # label: minute of the day where bar k starts
        m = X("XPR", f"p?(A+{k})*15:(B+{k})*60", {"p": q15, "A": quarter, "B": hour}, module=M, public=False)
        X("XPR", "A>=2880?A-2880:(A>=1440?A-1440:A)", {"A": m}, f"L{k}", M, desc=f"minute of the day, bar {k}")

# display values in the unit the operator chose (1 c/kWh = 10 EUR/MWh); inside everything stays c/kWh
fu = X("XPR", "A>0.5?10:1", {"A": unit_mwh}, "Unit_Factor", M)
for nm, src in (("Price", p_used), ("Avg", avg), ("Min", mn), ("Max", mx), ("N_Price", thr)):
    X("XPR", "A*B", {"A": src, "B": fu}, f"Disp_{nm}", M, desc="for display, in the chosen unit")

bad = p.check()
if bad:
    sys.exit("\n".join(bad))
p.layout()
p.save(os.path.join(HERE, "Spot.aut"))
json.dump(io, open(os.path.join(HERE, "io.json"), "w"), indent=1)
print(f"Spot.aut: {len(p.blocks)} blocks, {len(io['inputs'])} inputs, {len(io['public'])} public signals")
