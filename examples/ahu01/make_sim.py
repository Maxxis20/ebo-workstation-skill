#!/usr/bin/env python3
"""Plant simulation for AHU01: a Function Block program that plays the air handling unit, so that the AHU01
controller program can run in closed loop on a bench server.

    python3 make_sim.py   -> AHU01-SIM.aut, sim_io.json (prints stats and check)

Modules
- IN     one RI per physical output of the controller (AO and DO of DESCRIPTION.md 2.1), named by the tag.
         Bind IN/<tag> to the controller's Outputs/<tag>. Binary commands are read as > 0.5.
- PLANT  the model. Every physical input of the controller (AI and DI) is a public XPR / XPB named by the tag;
         bind the controller's Inputs/<tag> to PLANT/<tag>. Model states are public too (for trends and graphics).
- TEST   operator test conditions and fault injection (public PVR / PVB / PVI, defaults = healthy plant, -5 degC).

Model: model/MODEL.md and model/params.json; relations and numbers as implemented are listed in SIM_NOTES.md.
check_sim.py recomputes the static part in plain Python from the same numbers (PAR below).

Every lag that must change its time constant (running / stopped) is written as
    y = FILT( f ? x : y + (x - y) * Tb / T , Tb )        Tb = 20 s
which is a first-order lag of time constant about T (T >= Tb), with T chosen per cycle; f ("settling", the
first SETTLE_TIME seconds after program start or after TEST/Settle is switched 0 -> 1) makes every such lag run
at Tb, so the plant reaches its operating values within a couple of minutes whatever FILT starts from.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from aut import Program, expr_inputs

C = "\xb0C"
TB = 20                                  # base time constant of the variable lags, s

# ---- model numbers (MODEL.md / params.json; "a" = assumed here, beyond MODEL.md) ---------------------------------
PAR = dict(
    k_ps=368, k_pe=491, k_fs=1627, k_fe=2182,         # Pa at 100 % speed [fitted]
    off_pe=1.5, off_pd=8.0,                           # zero offsets PE1/PE2/PDE4 and PDE10/PDE20 [fitted]
    K_flow=350,                                       # l/s per sqrt(Pa) [from the program]
    hr_c=4.908, hr_x=0.452,                           # PDE4 = c * PDE20**x [fitted]
    ice_max=1.5, ice_T=-5.0, ice_u=50.0,              # frost term [assumed, MODEL 2]
    k_f=150,                                          # filter dp at 100 % clean [assumed]
    eta_s=0.616, eta_e=0.713, u0=17.5, uc=10.0,       # rotary wheel [fitted]
    hc_pass=0.73, eps_h=0.16, hh_u=20.0,              # heating coil [fitted given Twh = 50]
    rw_b=0.157, rw_T=23.0, k_rw=0.27, rw_off=18.5,    # return water TE1 [fitted]
    eps_c=0.48, hc_u=5.0, cc_off=-0.06, cc_min=3.0,   # cooling coil [fitted / assumed]
    fan_heat=0.1, fan_heat_n=60.0,                    # TE2 - TE5 at 60 % speed [fitted], proportional to speed (a)
    x_run=-0.42, x_off=-3.2,                          # TE7 - room [fitted]
    r_base=20.69, r_o=0.057, r_int=0.35, r_s=0.3,     # room [fitted / assumed]
    o1=0.8, o2=0.2, o3=-1.0,                          # TE10_x - room [fitted]
    mech=11.1, mech_o=0.3,                            # TE6 while stopped = 11.1 + 0.3 * T_o [fitted / assumed]
    off_TE2=19.6, off_TE3=17.0, off_TE4=18.4, off_TE5=19.1, off_TE8=13.9,   # stopped air temperatures [fitted]
    air_min=5.0,                                      # effective fan speed % above which air moves (a)
    broken=-199.0,                                    # value of a broken temperature sensor (a)
)
# time constants, s: (running, stopped)
TAU = dict(TE6=(300, 3600), TE3=(60, 1800), TE8=(60, 1800), TE4=(90, 1800), TE5=(90, 1800), TE2=(45, 1800),
           TE7=(300, 3000), TE1=(780, 300))           # TE1: (pumped, stagnant water in moving air)

# ---- interface ---------------------------------------------------------------------------------------------
READS_AO = ["TF01_Ctrl", "PF01_Ctrl", "SC3_Ctrl", "TV1_Ctrl", "TV2_Ctrl"]
READS_DO = ["FZ01_Cmd", "FZ02_Cmd", "TF01_Cmd", "PF01_Cmd", "SC3_Cmd", "P1_Cmd"]
AI = ["TE00", "TE1", "TE2", "TE3", "TE4", "TE5", "TE6", "TE7", "TE8", "TE10_1", "TE10_2", "TE10_3",
      "PE1", "PE2", "PDE1", "PDE2", "PDE3", "PDE4", "PDE10", "PDE20"]
DI = ["FA01", "SB01", "HS10", "P1_Fdb", "TF01_Fdb", "PF01_Fdb", "SC3_Fault", "Reset_DI"]
FAULT_SENSORS = ["TE00", "TE1", "TE2", "TE3", "TE6", "TE7", "TE10_1"]

# TEST values: name, kind, default, unit, meaning
TESTS = [
    ("OT_Manual", "PVR", -5.0, C, "Outdoor temperature; with OT_Profile 1 or 2 the mean of the profile"),
    ("OT_Profile", "PVI", 0, "", "0 = OT_Manual as is, 1 = sine around OT_Manual (peak at 15:00 for a 24 h period), 2 = sawtooth (rises from mean - A to mean + A over one period)"),
    ("OT_Amplitude", "PVR", 4.0, "", "Profile amplitude A, K"),
    ("OT_Period", "PVR", 24.0, "", "Profile period, h (use a divisor of 24 so that it is continuous at midnight)"),
    ("Room_Load", "PVR", 0.0, "", "Room load dT_load added to the room temperature target, K (+2 occupancy/solar, -2 cold)"),
    ("Room_Tau", "PVR", 10800.0, "s", "Room time constant, s (10800 for tests, 183600 = 51 h as fitted)"),
    ("HW_Supply_T", "PVR", 50.0, C, "Heating coil water supply temperature (drop to provoke a freeze trip)"),
    ("HC_Capacity", "PVR", 2.5, "", "Heating coil size factor on the fitted effectiveness 0.16 (1 = as fitted: too small to heat alone at -5 degC)"),
    ("CC_Water_T", "PVR", 7.0, C, "Cooling coil water temperature (7 chilled; 30 for warm water with controller Heating_Mode = 1)"),
    ("Dirt_PDE1", "PVR", 1.0, "", "Supply filter stage 2 dirt factor (1 clean ... 2.5 dirty; alarm from about 1.75 at 60 %)"),
    ("Dirt_PDE3", "PVR", 1.0, "", "Supply filter stage 1 dirt factor"),
    ("Dirt_PDE2", "PVR", 1.0, "", "Extract filter dirt factor"),
    ("Ice_Auto", "PVB", 0, "", "1 = icing builds by the MODEL.md rule (outdoor below -5 degC and rotor above 50 %); 0 = no icing (as in the recorded data)"),
    ("Ice_Force", "PVB", 0, "", "1 = heat recovery icing builds regardless of temperature (PDE4 rises, time constant Ice_Tau)"),
    ("Noise_On", "PVB", 0, "", "1 = sensor noise on (0.03 K on temperatures, 1 % on pressures)"),
    ("Settle", "PVB", 1, "", "While 1: the first Settle_Time s after program start or after a 0 -> 1 switch all slow lags run at 20 s"),
    ("Fire_Alarm", "PVB", 0, "", "1 = fire panel contact opens (FA01 = 0)"),
    ("Stop_Pressed", "PVB", 0, "", "1 = emergency stop pressed (SB01 = 0)"),
    ("HS10_Press", "PVB", 0, "", "1 = extended run button held (HS10 = 1); set 1 then 0 for a press"),
    ("Reset_Press", "PVB", 0, "", "1 = panel reset button held (Reset_DI = 1); set 1 then 0"),
    ("TF01_Fail", "PVB", 0, "", "1 = supply fan drive trips: fan stops, TF01_Fdb = 0"),
    ("PF01_Fail", "PVB", 0, "", "1 = extract fan drive trips: fan stops, PF01_Fdb = 0"),
    ("P1_Fail", "PVB", 0, "", "1 = pump P1 fails: no circulation, P1_Fdb = 0"),
    ("SC3_Fail", "PVB", 0, "", "1 = heat exchanger drive fault: rotor stops, SC3_Fault = 0"),
    ("HN_Pres_Alarm", "PVB", 0, "", "1 = heat supply pressure alarm on PLANT/HN_Pres_In (optional binding)"),
    ("HN_Temp_Alarm", "PVB", 0, "", "1 = heat supply temperature alarm on PLANT/HN_Temp_In (optional binding)"),
]
for t in FAULT_SENSORS:
    TESTS.append((f"{t}_Offset", "PVR", 0.0, "", f"Offset added to {t}, K"))
    TESTS.append((f"{t}_Broken", "PVB", 0, "", f"1 = {t} broken, reads {PAR['broken']:g} degC"))

CONSTS = [("Fan_Ramp", 3.333, "", "fan drive ramp, %/s (0-100 % in 30 s)"),
          ("Damper_Rate", 1.111, "", "damper travel, %/s (90 s stroke)"),
          ("Valve_Rate", 0.8333, "", "valve travel, %/s (120 s stroke)"),
          ("P_Tau", 5, "s", "duct pressure lag"),
          ("Ice_Tau", 3600, "s", "heat recovery icing time constant"),
          ("Fdb_Delay", 3, "s", "fan drive running feedback delay"),
          ("Pump_Fdb_Delay", 2, "s", "pump running feedback delay"),
          ("Settle_Time", 600, "s", "fast settling time after start")]


def g(v):
    """A number for an expression text: short, never in exponent notation."""
    s = f"{v:.4g}"
    if "e" in s:
        s = f"{v:.6f}".rstrip("0")
    return s


def build():
    p = Program("AHU01-SIM")
    P = "PLANT"

    def X(expr, ins, name="", public=False, unit="", typ="XPR"):
        b = p.block(typ, name, [expr], unit=unit, public=public, module=P)
        if sorted(ins, key=str.lower) != expr_inputs(expr):
            raise ValueError(f"{name or expr}: inputs {sorted(ins)} vs {expr_inputs(expr)}")
        for k, s in ins.items():            # None: wired later (feedback through a FILT)
            if s is not None:
                p.wire(s, b, k)
        return b

    def XB(expr, ins, name="", public=False):
        return X(expr, ins, name, public, typ="XPB")

    def blk(typ, src, params, name="", public=False, unit=""):
        b = p.block(typ, name, params, unit=unit, public=public, module=P)
        p.wire(src, b)
        return b

    for n, v, u, _d in CONSTS:
        p.const(n, v, u)

    # IN: the controller's outputs
    IN = {t: p.block("RI", t, params=[0], unit="%", public=True, module="IN") for t in READS_AO}
    IN.update({t: p.block("RI", t, params=[0], public=True, module="IN") for t in READS_DO})

    # TEST
    T = {}
    for n, typ, v, u, _m in TESTS:
        T[n] = p.block(typ, n, params=[v], unit=u, public=True, module="TEST")

    # settling flag: Settle and not yet Settle_Time s since it became 1
    sd = p.block("DELAY", "", ["Settle_Time", 0], module=P); p.wire(T["Settle"], sd)
    fast = XB("s&!d", {"s": T["Settle"], "d": sd}, "Settling", True)

    def lag(name, target, taus, cond, unit=C):
        """First-order lag, time constant taus[0] while cond, taus[1] otherwise (see module doc)."""
        k1, k2 = TB / taus[0], TB / taus[1]
        xp = X(f"f?X:Y+(X-Y)*(c?{g(k1)}:{g(k2)})", {"f": fast, "X": target, "c": cond, "Y": None})
        y = p.block("FILT", name, [TB], unit=unit, public=True, module=P)
        p.wire(xp, y); p.wire(y, xp, "Y")
        return y

    # clock and noise
    sec = X("3600*H+60*M+S", {"H": p.block("HOUR", "", module=P), "M": p.block("MINUTE", "", module=P),
                              "S": p.block("SECOND", "", module=P)}, "Day_Seconds", True, "s")
    n1 = X("n?(SIN(1.3*T)+SIN(2.9*T+1)+SIN(4.7*T+2))/3:0", {"n": T["Noise_On"], "T": sec}, "Noise1", True)
    n2 = X("n?(SIN(1.7*T+3)+SIN(3.1*T+2)+SIN(5.3*T))/3:0", {"n": T["Noise_On"], "T": sec}, "Noise2", True)

    def sensor(tag, src, kind, noise, off=0.0):
        """Public signal of a controller input: value + fixed offset + noise (+ test offset / broken switch)."""
        o = f"+{g(off)}" if off > 0 else (f"-{g(-off)}" if off < 0 else "")
        if kind == "P":
            return X(f"A{o}+0.024*A*N", {"A": src, "N": noise}, tag, True, "Pa")
        if tag in FAULT_SENSORS:
            return X(f"f?{g(PAR['broken'])}:A{o}+O+0.073*N",
                     {"f": T[f"{tag}_Broken"], "A": src, "O": T[f"{tag}_Offset"], "N": noise}, tag, True, C)
        return X(f"A{o}+0.073*N", {"A": src, "N": noise}, tag, True, C)

    # outdoor
    per = blk("LIMIT", T["OT_Period"], [0.1, 240])
    ph = X("(S+32400)/(3600*P)", {"S": sec, "P": per})
    ot_raw = X("Q<0.5?M:(Q<1.5?M+A*COS(6.2832*X):M+A*(2*(X-INT(X))-1))",
               {"Q": T["OT_Profile"], "M": T["OT_Manual"], "A": T["OT_Amplitude"], "X": ph})
    To = blk("LIMIT", ot_raw, [-40, 45], "T_Out", True, C)

    # dampers
    def damper(tag):
        t = X("A>0.5?100:0", {"A": IN[tag + "_Cmd"]})
        return blk("RAMP", t, ["Damper_Rate"], tag + "_Pos", True, "%")
    fz1, fz2 = damper("FZ01"), damper("FZ02")

    # fans: speed ramp, effective speed through the damper, pressures, feedback
    def fan(tag, dmp, fail):
        on = XB("A>0.5&!f", {"A": IN[tag + "_Cmd"], "f": fail})
        tgt = blk("LIMIT", X("b?A:0", {"b": on, "A": IN[tag + "_Ctrl"]}), [0, 100])
        spd = blk("RAMP", tgt, ["Fan_Ramp"], tag + "_Speed", True, "%")
        eff = X("A*B/100", {"A": spd, "B": dmp}, tag + "_Eff", True, "%")
        fdb = XB("d", {"d": blk("DELAY", on, ["Fdb_Delay", "Fdb_Delay"])}, tag + "_Fdb", True)
        air = XB(f"A>{g(PAR['air_min'])}", {"A": eff}, tag + "_Air", True)
        return eff, air, fdb

    ns, air_s, _ = fan("TF01", fz1, T["TF01_Fail"])
    ne, air_e, _ = fan("PF01", fz2, T["PF01_Fail"])

    def press(tag, k, n, noise, off, dirt=None):
        if dirt is None:
            raw = X(f"{g(k)}*(A/100)**2", {"A": n})
        else:
            raw = X(f"{g(k)}*(A/100)**2*D", {"A": n, "D": dirt})
        m = blk("FILT", raw, ["P_Tau"], tag + "_M", True, "Pa")
        sensor(tag, m, "P", noise, off)
        return raw, m

    press("PE1", PAR["k_ps"], ns, n1, PAR["off_pe"])
    press("PE2", PAR["k_pe"], ne, n2, PAR["off_pe"])
    _, pd10 = press("PDE10", PAR["k_fs"], ns, n2, PAR["off_pd"])
    dfe, pd20 = press("PDE20", PAR["k_fe"], ne, n1, PAR["off_pd"])
    press("PDE3", PAR["k_f"], ns, n1, 0, T["Dirt_PDE3"])
    press("PDE1", PAR["k_f"], ns, n2, 0, T["Dirt_PDE1"])
    press("PDE2", PAR["k_f"], ne, n1, 0, T["Dirt_PDE2"])
    X(f"{g(PAR['K_flow'] / 1000)}*SQRT(A+{g(PAR['off_pd'])})", {"A": pd10}, "Supply_Flow", True)
    X(f"{g(PAR['K_flow'] / 1000)}*SQRT(A+{g(PAR['off_pd'])})", {"A": pd20}, "Exhaust_Flow", True)

    # heat recovery wheel
    sc_on = XB("A>0.5&!f", {"A": IN["SC3_Cmd"], "f": T["SC3_Fail"]})
    u = blk("LIMIT", X("b?A:0", {"b": sc_on, "A": IN["SC3_Ctrl"]}), [0, 100], "SC3_Speed", True, "%")
    eta = X(f"A<={g(PAR['u0'])}?0:{g(PAR['eta_s'])}*(1-EXP(({g(PAR['u0'])}-A)/{g(PAR['uc'])}))",
            {"A": u}, "Eta_HR", True)
    XB("!f", {"f": T["SC3_Fail"]}, "SC3_Fault", True)
    ice_t = X(f"(((A<{g(PAR['ice_T'])})&(B>{g(PAR['ice_u'])})&e)|f)?{g(PAR['ice_max'])}:0",
              {"A": To, "B": u, "e": T["Ice_Auto"], "f": T["Ice_Force"]})
    ice = blk("FILT", ice_t, ["Ice_Tau"], "HR_Ice", True)
    pd4 = blk("FILT", X(f"{g(PAR['hr_c'])}*(D+0.01)**{g(PAR['hr_x'])}*(1+I)", {"D": dfe, "I": ice}),
              ["P_Tau"], "PDE4_M", True, "Pa")
    sensor("PDE4", pd4, "P", n2, PAR["off_pe"])

    # pump
    p_on = XB("A>0.5&!f", {"A": IN["P1_Cmd"], "f": T["P1_Fail"]})
    pr = XB("d", {"d": blk("DELAY", p_on, ["Pump_Fdb_Delay", "Pump_Fdb_Delay"])}, "P1_Fdb", True)

    # valves
    def valve(tag):
        return blk("RAMP", blk("LIMIT", IN[tag + "_Ctrl"], [0, 100]), ["Valve_Rate"], tag + "_Pos", True, "%")
    tv1, tv2 = valve("TV1"), valve("TV2")
    hh = X(f"(1-EXP(-A/{g(PAR['hh_u'])}))/0.99326", {"A": tv1}, "HC_Char", True)
    hc = X(f"1-EXP(-A/{g(PAR['hc_u'])})", {"A": tv2}, "CC_Char", True)

    # air temperatures (TE7 and the room close the loop, so their states are made first and wired later)
    t6 = lag("TE6_M", X(f"a?O:{g(PAR['mech'])}+{g(PAR['mech_o'])}*O", {"a": air_s, "O": To}), TAU["TE6"], air_s)
    # extract air TE7 = room - 0.42 running, room - 3.2 stopped
    t7_tgt = X(f"a?R{g(PAR['x_run'])}:R{g(PAR['x_off'])}", {"a": air_e, "R": None})
    t7 = lag("TE7_M", t7_tgt, TAU["TE7"], air_e)
    t3 = lag("TE3_M", X(f"a?B+E*(C-B):{g(PAR['off_TE3'])}", {"a": air_s, "B": t6, "E": eta, "C": t7}),
             TAU["TE3"], air_s)
    t8 = lag("TE8_M", X(f"a?C-{g(PAR['eta_e'] / PAR['eta_s'])}*E*(C-B):{g(PAR['off_TE8'])}",
                        {"a": air_e, "B": t6, "E": eta, "C": t7}), TAU["TE8"], air_e)
    t4 = lag("TE4_M", X(f"a?B+(p?{g(PAR['hc_pass'])}+{g(PAR['eps_h'])}*K*H*(W-B):0):{g(PAR['off_TE4'])}",
                        {"a": air_s, "B": t3, "p": pr, "K": T["HC_Capacity"], "H": hh, "W": T["HW_Supply_T"]}),
             TAU["TE4"], air_s)
    # return water: reference = air after the wheel while air moves, plant room level while stopped
    rref = X(f"a?B:{g(PAR['rw_off'])}", {"a": air_s, "B": t3})
    t1_tgt = X(f"p?C+(a?{g(PAR['rw_b'])}*({g(PAR['rw_T'])}-C):0)+{g(PAR['k_rw'])}*H*(W-C):C",
               {"p": pr, "C": rref, "a": air_s, "H": hh, "W": T["HW_Supply_T"]})
    stag = XB("a&!p", {"a": air_s, "p": pr})
    t1 = lag("TE1_M", t1_tgt, (TAU["TE1"][1], TAU["TE1"][0]), stag)
    # cooling coil: leaving air not below min(entering - 0.06, water + 3)
    ccx = X(f"B+{g(PAR['eps_c'])}*H*(W-B){g(PAR['cc_off'])}", {"B": t4, "H": hc, "W": T["CC_Water_T"]})
    ccl = X(f"W+{g(PAR['cc_min'])}<B?W+{g(PAR['cc_min'])}:B{g(PAR['cc_off'])}", {"W": T["CC_Water_T"], "B": t4})
    t5 = lag("TE5_M", X(f"a?(X<L?L:X):{g(PAR['off_TE5'])}", {"a": air_s, "X": ccx, "L": ccl}), TAU["TE5"], air_s)
    t2 = lag("TE2_M", X(f"a?B+{g(PAR['fan_heat'] / PAR['fan_heat_n'])}*N:{g(PAR['off_TE2'])}",
                        {"a": air_s, "B": t5, "N": ns}), TAU["TE2"], air_s)
    # room
    r_tgt = X(f"{g(PAR['r_base'])}+{g(PAR['r_o'])}*O+(a?{g(PAR['r_s'])}*(B-{g(PAR['r_base'])})+{g(PAR['r_int'])}:0)+L",
              {"O": To, "a": air_s, "B": t2, "L": T["Room_Load"]})
    rtau = blk("LIMIT", T["Room_Tau"], [TB, 1000000])
    rx = X("f?X:Y+(X-Y)*20/T", {"f": fast, "X": r_tgt, "T": rtau, "Y": None})
    room = p.block("FILT", "Room_T", [TB], unit=C, public=True, module=P)
    p.wire(rx, room); p.wire(room, rx, "Y")
    p.wire(room, t7_tgt, "R")

    # controller inputs
    sensor("TE00", To, "T", n1)
    sensor("TE1", t1, "T", n2)
    sensor("TE2", t2, "T", n1)
    sensor("TE3", t3, "T", n2)
    sensor("TE4", t4, "T", n1)
    sensor("TE5", t5, "T", n2)
    sensor("TE6", t6, "T", n1)
    sensor("TE7", t7, "T", n2)
    sensor("TE8", t8, "T", n1)
    sensor("TE10_1", room, "T", n2, PAR["o1"])
    sensor("TE10_2", room, "T", n1, PAR["o2"])
    sensor("TE10_3", room, "T", n2, PAR["o3"])
    XB("!f", {"f": T["Fire_Alarm"]}, "FA01", True)
    XB("!f", {"f": T["Stop_Pressed"]}, "SB01", True)
    XB("h", {"h": T["HS10_Press"]}, "HS10", True)
    XB("r", {"r": T["Reset_Press"]}, "Reset_DI", True)
    XB("a", {"a": T["HN_Pres_Alarm"]}, "HN_Pres_In", True)
    XB("a", {"a": T["HN_Temp_Alarm"]}, "HN_Temp_In", True)
    return p


def sim_io():
    return {
        "reads": READS_AO + READS_DO,
        "provides": [{"tag": t, "kind": "analog", "signal": f"PLANT/{t}"} for t in AI]
                    + [{"tag": t, "kind": "binary", "signal": f"PLANT/{t}"} for t in DI],
        "optional_provides": [
            {"tag": "HN_Pres_In", "kind": "binary", "signal": "PLANT/HN_Pres_In",
             "note": "soft input of the controller (Inputs/HN_Pres_In); bind only to test the heat supply alarms"},
            {"tag": "HN_Temp_In", "kind": "binary", "signal": "PLANT/HN_Temp_In",
             "note": "soft input of the controller (Inputs/HN_Temp_In); bind only to test the heat supply alarms"}],
        "test": [{"path": f"TEST/{n}", "default": v, "unit": u.replace(C, "degC"), "meaning": m}
                 for n, _t, v, u, m in TESTS],
        "constants": [{"name": n, "value": v, "unit": u, "meaning": m} for n, v, u, m in CONSTS],
    }


if __name__ == "__main__":
    p = build()
    names = {b.full_name for b in p.all_blocks()}
    missing = [t for t in AI + DI if f"PLANT\\{t}" not in names] + [t for t in READS_AO + READS_DO if f"IN\\{t}" not in names]
    assert not missing, missing
    assert all(len(b.name) <= 20 for b in p.all_blocks()), [b.name for b in p.all_blocks() if len(b.name) > 20]
    p.save(os.path.join(HERE, "AHU01-SIM.aut"))
    with open(os.path.join(HERE, "sim_io.json"), "w") as f:
        json.dump(sim_io(), f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(p.stats())
    print(p.check())
