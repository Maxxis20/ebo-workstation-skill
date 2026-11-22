#!/usr/bin/env python3
"""Static check of the AHU01 plant simulation: the relations of make_sim.py re-implemented in plain Python.

    python3 check_sim.py

Numbers come from make_sim.PAR / TESTS (one source); the relations are written again here, as steady state
(every lag settled, ramps at their targets, dampers at their end positions, sensor noise off).

Part 1: plant outputs for four fixed sets of controller outputs.
Part 2: closed-loop steady state with a simple model of the controller's steady behaviour (pressure loops at their
setpoint or output limit, the supply temperature sequence integrated until TE2 = setpoint, return water control,
pump need), for the test scenarios of SIM_NOTES.md.
"""
import math
from make_sim import PAR as K, TESTS

DEF = {n: v for n, _t, v, _u, _m in TESTS}


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def prcnt(x, v0, v100):
    return clamp((x - v0) / (v100 - v0) * 100, 0, 100)


def plant(o, t=None, ice_on=None):
    """Steady-state plant. o: controller outputs (TF01_Ctrl ... P1_Cmd). t: TEST values (defaults filled in)."""
    t = dict(DEF, **(t or {}))
    To = clamp(t["OT_Manual"], -40, 45)
    d1 = 100 if o.get("FZ01_Cmd") else 0
    d2 = 100 if o.get("FZ02_Cmd") else 0
    sp_s = clamp(o.get("TF01_Ctrl", 0), 0, 100) if o.get("TF01_Cmd") and not t["TF01_Fail"] else 0
    sp_e = clamp(o.get("PF01_Ctrl", 0), 0, 100) if o.get("PF01_Cmd") and not t["PF01_Fail"] else 0
    ns, ne = sp_s * d1 / 100, sp_e * d2 / 100
    air_s, air_e = ns > K["air_min"], ne > K["air_min"]
    r = {}
    r["PE1"] = K["k_ps"] * (ns / 100) ** 2 + K["off_pe"]
    r["PE2"] = K["k_pe"] * (ne / 100) ** 2 + K["off_pe"]
    r["PDE10"] = K["k_fs"] * (ns / 100) ** 2 + K["off_pd"]
    dfe = K["k_fe"] * (ne / 100) ** 2
    r["PDE20"] = dfe + K["off_pd"]
    r["PDE3"] = K["k_f"] * (ns / 100) ** 2 * t["Dirt_PDE3"]
    r["PDE1"] = K["k_f"] * (ns / 100) ** 2 * t["Dirt_PDE1"]
    r["PDE2"] = K["k_f"] * (ne / 100) ** 2 * t["Dirt_PDE2"]
    r["Supply_Flow"] = K["K_flow"] / 1000 * math.sqrt(r["PDE10"])
    r["Exhaust_Flow"] = K["K_flow"] / 1000 * math.sqrt(r["PDE20"])
    u = clamp(o.get("SC3_Ctrl", 0), 0, 100) if o.get("SC3_Cmd") and not t["SC3_Fail"] else 0
    eta = 0 if u <= K["u0"] else K["eta_s"] * (1 - math.exp((K["u0"] - u) / K["uc"]))
    if ice_on is None:
        ice_on = (To < K["ice_T"] and u > K["ice_u"] and t["Ice_Auto"]) or t["Ice_Force"]
    ice = K["ice_max"] if ice_on else 0
    r["PDE4"] = K["hr_c"] * (dfe + 0.01) ** K["hr_x"] * (1 + ice) + K["off_pe"]
    pump = bool(o.get("P1_Cmd")) and not t["P1_Fail"]
    hh = (1 - math.exp(-clamp(o.get("TV1_Ctrl", 0), 0, 100) / K["hh_u"])) / 0.99326
    hc = 1 - math.exp(-clamp(o.get("TV2_Ctrl", 0), 0, 100) / K["hc_u"])
    Tw, Tc = t["HW_Supply_T"], t["CC_Water_T"]
    T6 = To if air_s else K["mech"] + K["mech_o"] * To
    room = K["r_base"]
    for _ in range(300):                                  # room <-> supply air fixed point
        T7 = room + (K["x_run"] if air_e else K["x_off"])
        T3 = T6 + eta * (T7 - T6) if air_s else K["off_TE3"]
        T8 = T7 - K["eta_e"] / K["eta_s"] * eta * (T7 - T6) if air_e else K["off_TE8"]
        T4 = (T3 + ((K["hc_pass"] + K["eps_h"] * t["HC_Capacity"] * hh * (Tw - T3)) if pump else 0)
              if air_s else K["off_TE4"])
        ref = T3 if air_s else K["rw_off"]
        T1 = ref + ((K["rw_b"] * (K["rw_T"] - ref) if air_s else 0) + K["k_rw"] * hh * (Tw - ref)) if pump else ref
        x = T4 + K["eps_c"] * hc * (Tc - T4) + K["cc_off"]
        lo = Tc + K["cc_min"] if Tc + K["cc_min"] < T4 else T4 + K["cc_off"]
        T5 = max(x, lo) if air_s else K["off_TE5"]
        T2 = T5 + K["fan_heat"] / K["fan_heat_n"] * ns if air_s else K["off_TE2"]
        new = (K["r_base"] + K["r_o"] * To + (K["r_s"] * (T2 - K["r_base"]) + K["r_int"] if air_s else 0)
               + t["Room_Load"])
        if abs(new - room) < 1e-9:
            break
        room = new
    r.update(TE00=To, TE1=T1, TE2=T2, TE3=T3, TE4=T4, TE5=T5, TE6=T6, TE7=T7, TE8=T8, Room_T=room,
             TE10_1=room + K["o1"], TE10_2=room + K["o2"], TE10_3=room + K["o3"], Eta_HR=eta, HR_Ice=ice)
    r["Eff_meas"] = (T3 - T6) / (T7 - T6) * 100 if air_s and T7 - T6 >= 3 else 0
    r.update(FA01=int(not t["Fire_Alarm"]), SB01=int(not t["Stop_Pressed"]), SC3_Fault=int(not t["SC3_Fail"]),
             P1_Fdb=int(pump), TF01_Fdb=int(bool(o.get("TF01_Cmd")) and not t["TF01_Fail"]),
             PF01_Fdb=int(bool(o.get("PF01_Cmd")) and not t["PF01_Fail"]))
    return r


# ---- simple steady-state controller (DESCRIPTION.md 4.8 ... 4.12, defaults) -------------------------------------
def temp_sp(te7):
    return clamp(21.5 + (te7 - 18.0) * (16.0 - 21.5) / (23.0 - 18.0), 16.0, 21.5)


def fan_speed(sp, k, off):
    return clamp(100 * math.sqrt(max(sp - off, 0) / k), 20, 60)


def controller(t=None, season=0, heating_mode=0):
    """Closed-loop steady state: returns (controller outputs, plant result, notes)."""
    t = dict(DEF, **(t or {}))
    To = t["OT_Manual"]
    base = dict(FZ01_Cmd=1, FZ02_Cmd=1, TF01_Cmd=1, PF01_Cmd=1,
                TF01_Ctrl=fan_speed(80, K["k_ps"], K["off_pe"]), PF01_Ctrl=fan_speed(60, K["k_pe"], K["off_pe"]))
    tv1_min = 0.0
    notes = []

    def outputs(s):
        o = dict(base)
        if season == 0:
            if heating_mode:
                sc3, tv2, tv1 = prcnt(s, 10, 45), prcnt(s, 50, 100), prcnt(s, 100, 150)
            else:
                sc3, tv2, tv1 = prcnt(s, 10, 75), 0.0, prcnt(s, 75, 145)
        else:
            sc3, tv2, tv1 = prcnt(s, 10, 100), prcnt(s, -10, -50), prcnt(s, 100, 150)
            if cool_rec:
                sc3, tv2 = max(sc3, prcnt(s, -10, -30)), prcnt(s, -30, -50)
        o.update(SC3_Ctrl=sc3, SC3_Cmd=int(sc3 > 1), TV2_Ctrl=tv2, TV1_Ctrl=max(tv1, tv1_min))
        o["P1_Cmd"] = int(To <= 10 or o["TV1_Ctrl"] > 0)
        return o

    def err(s):
        r = plant(outputs(s), t)
        return r["TE2"] - temp_sp(r["TE7"]), r

    cool_rec = False
    lo, hi = (-10, 150) if season == 0 else (-50, 150)
    for _pass in range(4):
        if err(lo)[0] > 0:
            s = lo; notes.append("sequence at its lower limit (supply warmer than setpoint)")
        elif err(hi)[0] < 0:
            s = hi; notes.append("sequence at its upper limit (supply colder than setpoint)")
        else:
            a, b = lo, hi
            for _ in range(80):
                m = (a + b) / 2
                a, b = (m, b) if err(m)[0] < 0 else (a, m)
            s = (a + b) / 2
        r = plant(outputs(s), t)
        if season == 1 and not cool_rec and r["TE7"] <= To - 2:   # Cool_Recovery latch sets
            cool_rec = True; notes.append("Cool_Recovery on")
            continue
        if r["TE1"] < 11 and outputs(s)["P1_Cmd"]:          # return water controller opens TV1
            a, b = 0.0, 100.0
            for _ in range(60):
                m = (a + b) / 2
                o = outputs(s); o["TV1_Ctrl"] = max(o["TV1_Ctrl"], m)
                a, b = (m, b) if plant(o, t)["TE1"] < 11 else (a, m)
            tv1_min = b
            notes.append(f"return water control holds TV1 >= {b:.1f} %")
        else:
            break
    o = outputs(s)
    r = plant(o, t)
    o["seq"] = s
    o["SP"] = temp_sp(r["TE7"])
    return o, r, sorted(set(notes))


def show_plant(title, o, t=None):
    r = plant(o, t)
    print(f"\n{title}")
    print("  outputs: " + ", ".join(f"{k}={v:g}" for k, v in o.items()))
    keys = ["TE00", "TE6", "TE3", "TE4", "TE5", "TE2", "TE1", "TE7", "TE8", "TE10_1", "TE10_2", "TE10_3",
            "PE1", "PE2", "PDE10", "PDE20", "PDE4", "PDE3", "PDE1", "PDE2"]
    print("  " + "  ".join(f"{k} {r[k]:.1f}" for k in keys))
    print(f"  flow s/e {r['Supply_Flow']:.2f}/{r['Exhaust_Flow']:.2f} m3/s, HR efficiency (TE3-TE6)/(TE7-TE6) "
          f"{r['Eff_meas']:.1f} %, room {r['Room_T']:.2f}")
    return r


def show_loop(title, t=None, season=0, heating_mode=0):
    o, r, notes = controller(t, season, heating_mode)
    print(f"\n{title}")
    print(f"  controller: TF01 {o['TF01_Ctrl']:.1f} %  PF01 {o['PF01_Ctrl']:.1f} %  SC3 {o['SC3_Ctrl']:.1f} %  "
          f"TV1 {o['TV1_Ctrl']:.1f} %  TV2 {o['TV2_Ctrl']:.1f} %  P1 {o['P1_Cmd']}  sequence {o['seq']:.1f}  "
          f"SP {o['SP']:.2f}")
    keys = ["TE00", "TE6", "TE3", "TE4", "TE5", "TE2", "TE1", "TE7", "TE8", "TE10_1", "TE10_2", "TE10_3",
            "PE1", "PE2", "PDE10", "PDE20", "PDE4", "PDE3", "PDE1", "PDE2"]
    print("  plant: " + "  ".join(f"{k} {r[k]:.1f}" for k in keys))
    print(f"  TE2-SP {r['TE2'] - o['SP']:+.2f} K, HR efficiency {r['Eff_meas']:.1f} %, PDE4 frost limit "
          f"{100 + 2 * o['PF01_Ctrl']:.0f} Pa, filter limit supply {10 + 1.4 * o['TF01_Ctrl']:.0f} / extract "
          f"{10 + 1.4 * o['PF01_Ctrl']:.0f} Pa, room {r['Room_T']:.2f}" + ("; " + "; ".join(notes) if notes else ""))
    return o, r


if __name__ == "__main__":
    print("=== Part 1: plant for fixed controller outputs (defaults, outdoor -5 degC) ===")
    run = dict(FZ01_Cmd=1, FZ02_Cmd=1, TF01_Cmd=1, PF01_Cmd=1, SC3_Cmd=1, P1_Cmd=1)
    show_plant("1a stopped (all outputs 0, pump off)", {})
    show_plant("1b stopped, freeze group (TV1 100 %, pump on)", dict(TV1_Ctrl=100, P1_Cmd=1))
    show_plant("1c running TF01 60 / PF01 45.9, SC3 100, TV1 0", dict(run, TF01_Ctrl=60, PF01_Ctrl=45.9, SC3_Ctrl=100))
    show_plant("1d running TF01 60 / PF01 45.9, SC3 100, TV1 100", dict(run, TF01_Ctrl=60, PF01_Ctrl=45.9, SC3_Ctrl=100, TV1_Ctrl=100))
    show_plant("1e running TF01 40 / PF01 30, SC3 50, TV1 30, TV2 50, chilled water", dict(run, TF01_Ctrl=40, PF01_Ctrl=30, SC3_Ctrl=50, TV1_Ctrl=30, TV2_Ctrl=50))

    print("\n=== Part 2: closed loop steady state (controller defaults, AOM 2 running) ===")
    show_loop("2a DEFAULTS: -5 degC, heating season, Heating_Mode 0")
    show_loop("2b cold -15 degC", dict(OT_Manual=-15))
    show_loop("2c design cold -20 degC", dict(OT_Manual=-20))
    show_loop("2d mild +8 degC (heating season)", dict(OT_Manual=8))
    show_loop("2e summer +25 degC, cooling season, chilled water 7 degC", dict(OT_Manual=25), season=1)
    show_loop("2f summer +28 degC, Room_Load -3 (cool recovery case)", dict(OT_Manual=28, Room_Load=-3), season=1)
    show_loop("2g HC_Capacity 1 (coil as fitted), -5 degC", dict(HC_Capacity=1))
    show_loop("2h as recorded: HC_Capacity 1, CC_Water_T 30, controller Heating_Mode 1, -5 degC",
              dict(HC_Capacity=1, CC_Water_T=30), heating_mode=1)
    show_loop("2i Room_Load +2 K, -5 degC", dict(Room_Load=2))
    show_loop("2j SC3_Fail, -5 degC", dict(SC3_Fail=1))
    show_loop("2k SC3_Fail, -20 degC (freeze trip expected: TE1 or TE2 <= 7)", dict(SC3_Fail=1, OT_Manual=-20))
    show_loop("2l HW_Supply_T 15, -15 degC (weak heat)", dict(HW_Supply_T=15, OT_Manual=-15))
    show_loop("2l' HW_Supply_T 15, -20 degC", dict(HW_Supply_T=15, OT_Manual=-20))
    show_loop("2p Ice_Auto 1, -15 degC (icing by the MODEL.md rule, before the controller limits the rotor)", dict(Ice_Auto=1, OT_Manual=-15))
    show_loop("2m Ice_Force, -5 degC (PDE4 above the frost limit)", dict(Ice_Force=1))
    show_loop("2n Dirt 2.0 on all filters, -5 degC", dict(Dirt_PDE1=2, Dirt_PDE2=2, Dirt_PDE3=2))
    r = plant(dict(run, TF01_Ctrl=60, PF01_Ctrl=45.9, SC3_Ctrl=100, TV1_Ctrl=20), dict(P1_Fail=1))
    print(f"\n2o P1_Fail at -5 degC, TV1 20 %: TE1 -> {r['TE1']:.1f} (stagnant water at air temperature), "
          f"TE4 {r['TE4']:.1f}, P1_Fdb {r['P1_Fdb']}")
