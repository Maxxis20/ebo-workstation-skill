#!/usr/bin/env python3
"""Operator graphic (HMI) of AHU01 for EBO 7.1, from DESCRIPTION.md sections 1, 5, 6, 7 and 8.

    python3 make_hmi.py [--bench] [-o AHU01-HMI.tgml]   -> the graphic and hmi_binds.json

--bench adds the "Test bench" panel (outdoor temperature and fault switches of the plant simulation, TEST/...).
Every bind of the graphic is in the table BINDS below (bind name, target Module/Name, label, decimals, unit); the
drawing code uses only the bind names, so a target is corrected in one place. Blue numbers are operator setpoints:
a click on them opens EBO's change dialog.
"""
import os, sys, json, math, textwrap, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from tgml import Graphic
sys.path.insert(0, os.path.join(HERE, "..", "room-sensor"))
import roomface                                             # the room sensor faceplate, shared with examples/room-sensor

DEG = "\xb0C"
# --- the one table: bind name, target, label, decimals (None = binary / state), unit --------------------------------
BINDS = [
    # header and modes
    ("RUN", "Operation/Run", "Unit running", None, ""),
    ("RUN_MODE", "Operation/Run_Mode", "Run mode", 0, ""),
    ("AOM", "Operation/AOM", "Operating mode selector", 0, ""),
    ("SEASON_SEL", "Operation/Season_Sel", "Season selector", 0, ""),
    ("SEASON", "Operation/Season_Mode", "Season in use", None, ""),
    ("NIGHT_COOL", "Operation/Night_Cooling", "Night cooling", None, ""),
    ("NIGHT_HEAT", "Operation/Night_Heating", "Night heating", None, ""),
    ("HEAT_MODE", "Operation/Heating_Mode", "Warm water in cooling coil", None, ""),
    ("CRIT", "Alarms/Critical_Alarm", "Critical alarm", None, ""),
    ("RESET", "Inputs/Reset_Cmd", "Alarm reset", None, ""),
    # dampers
    ("FZ01", "Outputs/FZ01_Cmd", "Outdoor air damper", None, ""),
    ("FZ02", "Outputs/FZ02_Cmd", "Exhaust air damper", None, ""),
    # temperatures and their instant fault flags
    *[(t, f"Inputs/{t}", f"Temperature {t}", 1, DEG) for t in
      ("TE00", "TE1", "TE2", "TE3", "TE4", "TE5", "TE6", "TE7", "TE8", "TE10_1", "TE10_2", "TE10_3")],
    *[(f"{t}_BAD", f"Inputs/bad_{t}", f"Sensor fault {t}", None, "") for t in
      ("TE00", "TE1", "TE2", "TE3", "TE4", "TE5", "TE6", "TE7", "TE8", "TE10_1", "TE10_2", "TE10_3")],
    ("OT_DAY", "Inputs/OT_Day_Mean", "Previous day outdoor mean", 1, DEG),
    ("ROOM_AVG", "Inputs/Room_Avg", "Room mean", 1, DEG),
    # pressures, flows
    *[(p, f"Inputs/{p}", f"Pressure {p}", 0, "Pa") for p in ("PE1", "PE2", "PDE1", "PDE2", "PDE3", "PDE4", "PDE10", "PDE20")],
    ("PE1_SP", "FAN/Supply_Pressure_SP", "Supply pressure setpoint in use", 0, "Pa"),
    ("PE2_SP", "FAN/Exhaust_Pressure_SP", "Extract pressure setpoint in use", 0, "Pa"),
    ("Q_SUP", "Inputs/Supply_Flow", "Supply air flow", 2, "m3/s"),
    ("Q_EXH", "Inputs/Exhaust_Flow", "Extract air flow", 2, "m3/s"),
    # heat recovery
    ("SC3", "Outputs/SC3_Ctrl", "Rotor speed", 0, "%"),
    ("SC3_CMD", "Outputs/SC3_Cmd", "Rotor start", None, ""),
    ("SC3_OK", "Inputs/SC3_Fault", "Rotor drive healthy (1 = normal)", None, ""),
    ("FROST", "HRU/Frost_Active", "Rotor frost limit active", None, ""),
    ("PDE4_SP", "HRU/PDE4_SP", "Rotor frost pressure limit", 0, "Pa"),
    ("HRU_EFF", "HRU/HRU_Efficiency", "Heat recovery efficiency", 0, "%"),
    # coils
    ("TV1", "Outputs/TV1_Ctrl", "Heating valve", 0, "%"),
    ("P1_CMD", "Outputs/P1_Cmd", "Pump P1 command", None, ""),
    ("P1_FDB", "Inputs/P1_Fdb", "Pump P1 running", None, ""),
    ("FREEZE", "Alarms/Freeze_Latch", "Freeze protection tripped", None, ""),
    ("TV2", "Outputs/TV2_Ctrl", "Cooling valve", 0, "%"),
    # fans
    ("TF01", "Outputs/TF01_Ctrl", "Supply fan speed", 0, "%"),
    ("TF01_CMD", "Outputs/TF01_Cmd", "Supply fan start", None, ""),
    ("TF01_FDB", "Inputs/TF01_Fdb", "Supply fan running", None, ""),
    ("PF01", "Outputs/PF01_Ctrl", "Extract fan speed", 0, "%"),
    ("PF01_CMD", "Outputs/PF01_Cmd", "Extract fan start", None, ""),
    ("PF01_FDB", "Inputs/PF01_Fdb", "Extract fan running", None, ""),
    # supply temperature
    ("ACT_SP", "ST/Active_SP", "Supply temperature setpoint in use", 1, DEG),
    # zone and safety
    ("HS10", "Inputs/HS10", "Extended run button", None, ""),
    ("HS10_EXT", "Operation/HS10_Ext", "Extended run active", None, ""),
    ("SB01", "Inputs/SB01", "Emergency stop (1 = normal)", None, ""),
    ("FA01", "Inputs/FA01", "Fire alarm contact (1 = normal)", None, ""),
    # operator setpoints (section 8 "adjustable")
    ("PE1_SET", "FAN/Supply_Pressure_Set", "Supply duct pressure setpoint", 0, "Pa"),
    ("PE2_SET", "FAN/Exhaust_Pressure_Set", "Extract duct pressure setpoint", 0, "Pa"),
    ("ET_X1", "ST/ET_X1", "Curve point 1, extract air", 1, DEG),
    ("SP_Y1", "ST/SP_Y1", "Curve point 1, supply setpoint", 1, DEG),
    ("ET_X2", "ST/ET_X2", "Curve point 2, extract air", 1, DEG),
    ("SP_Y2", "ST/SP_Y2", "Curve point 2, supply setpoint", 1, DEG),
    ("COIL_ST", "ST/Coil_Heat_ST", "Coil return water minimum", 1, DEG),
    ("FREEZE_SP", "Inputs/Freeze_SP", "Freeze protection limit", 1, DEG),
    ("FROST_LIM", "ST/Frost_HRU_Ctrl", "Rotor speed limit in frost", 0, "%"),
]
# alarms of section 5: name, class, short label (bind name = alarm name, target Alarms/<name>)
ALARMS = [
    ("Freeze_Alm", "A", "Freeze protection"), ("Fire_Alm", "A", "Fire alarm FA01"),
    ("Stop_Alm", "A", "Emergency stop SB01"), ("P1_Alm", "A", "Pump P1 not running"),
    ("HN_Pres_Alm", "A", "Heat supply pressure"), ("HN_Temp_Alm", "A", "Heat supply temperature"),
    ("Supply_Fire_Alm", "A", "Supply air fire limit"), ("Exhaust_Fire_Alm", "A", "Extract air fire limit"),
    ("TE00_Alm", "B", "Sensor TE00"), *[(f"TE{i}_Alm", "B", f"Sensor TE{i}") for i in range(1, 9)],
    *[(f"TE10_{i}_Alm", "B", f"Sensor TE10.{i}") for i in range(1, 4)],
    ("Supply_Temp_Alm", "B", "Supply temp. deviation"), ("Supply_Pres_Alm", "B", "Supply pressure dev."),
    ("Exhaust_Pres_Alm", "B", "Extract pressure dev."), ("TF01_Alm", "B", "Supply fan TF01"),
    ("PF01_Alm", "B", "Extract fan PF01"), ("HRU_Alm", "B", "Rotor drive SC3"),
    ("HRU_Frost_Alm", "B", "Rotor icing"), ("HRU_Efficiency_Alm", "B", "Rotor efficiency low"),
    ("HeatR_Alm", "B", "Heating coil no effect"), ("CoolR_Alm", "B", "Cooling coil no effect"),
    ("PDE3_Alm", "C", "Supply filter 1 dirty"), ("PDE1_Alm", "C", "Supply filter 2 dirty"),
    ("PDE2_Alm", "C", "Extract filter dirty"),
]
BINDS += [(n, f"Alarms/{n}", label, None, "") for n, _, label in ALARMS]
# test bench (plant simulation program, module TEST): only with --bench
BENCH = [   # names as in make_sim.py TESTS (module TEST of AHU01-SIM)
    ("B_OT", "TEST/OT_Manual", "Outdoor temperature (test)", 1, DEG),
    ("B_HWT", "TEST/HW_Supply_T", "Heating coil water supply temperature", 0, DEG),
    ("B_FIRE", "TEST/Fire_Alarm", "Fire alarm (1 = fire)", None, ""),
    ("B_ESTOP", "TEST/Stop_Pressed", "Emergency stop pressed (1)", None, ""),
    ("B_P1F", "TEST/P1_Fail", "Pump P1 fails (1)", None, ""),
    ("B_SC3F", "TEST/SC3_Fail", "Rotor drive fault (1)", None, ""),
    ("B_TF01F", "TEST/TF01_Fail", "Supply fan drive trips (1)", None, ""),
    ("B_ICE", "TEST/Ice_Force", "Rotor icing forced (1)", None, ""),
]

# --- section 7 popup texts, as they are ------------------------------------------------------------------------------
POP = {
    "FZ01": ("FZ01 Outdoor air damper", "Shut-off damper at the outdoor air intake. It opens as soon as the unit is started and closes immediately when the unit stops or a critical alarm trips. It is an open/closed damper with spring return, so it also closes on power failure. The fans are only released after it has had time to open."),
    "FZ02": ("FZ02 Exhaust air damper", "Shut-off damper at the exhaust air outlet. It opens and closes together with the outdoor air damper. The extract fan is released 30 s after it opens. Closed when stopped and on power failure."),
    "TE00": ("TE00 Outdoor temperature", "Outdoor air temperature from a sensor outside the building. It is used for start-up pre-heat, the heating coil pump, the season changeover (daily mean), night cooling and night heating, cooling recovery and the optional fan low speed mode. A faulty sensor gives an alarm after 3 minutes; the unit then assumes 0 \xb0C and does not run the night modes."),
    "TE6": ("TE6 Intake air temperature", "Temperature of the outdoor air just behind the intake damper, before the filters. It is the cold side reference for the heat recovery efficiency and enables the heat recovery frost protection at 0 \xb0C and below. While the unit is stopped it shows plant room temperature rather than outdoor temperature."),
    "FLT1": ("Supply filter stage 1 (PDE3)", "First filter stage in the outdoor air. It keeps coarse dust away from the second stage and the coils. Its condition is supervised by the pressure drop PDE3."),
    "PDE3": ("PDE3 Filter pressure drop, stage 1", "Pressure difference across the first supply filter. An alarm \"filter dirty\" is given when the pressure drop has been above the limit for 5 minutes; the limit rises with the supply fan speed from 10 Pa at 0 % to 150 Pa at 100 %. The alarm can be switched off when no filter is fitted."),
    "FLT2": ("Supply filter stage 2 (PDE1)", "Second, finer filter stage in the outdoor air, before the heat recovery. Its condition is supervised by the pressure drop PDE1."),
    "PDE1": ("PDE1 Filter pressure drop, stage 2", "Pressure difference across the second supply filter. Alarm \"filter dirty\" after 5 minutes above the speed dependent limit (10 Pa at 0 % to 150 Pa at 100 % supply fan speed)."),
    "SC3": ("SC3 Rotary heat exchanger", "Rotating wheel that transfers heat (and in summer, cooling) from the extract air to the supply air. Its speed 0 ... 100 % is the first stage of the supply temperature sequence. At a cold start it runs at 100 % for 20 minutes. When ice builds on the extract side its speed is limited to 50 %. A drive fault gives an alarm after 3 minutes."),
    "PDE4": ("PDE4 Heat exchanger pressure drop", "Pressure difference across the extract side of the rotor. It rises when ice builds up. At intake temperature 0 \xb0C or below, a value above the limit (100 Pa at 0 % to 300 Pa at 100 % extract fan speed) activates frost protection: rotor speed limited to 50 % and alarm after 3 minutes."),
    "EFF": ("HRU efficiency", "Calculated temperature efficiency of the heat recovery, (TE3 - TE6) / (TE7 - TE6). Shown only when the rotor runs above 50 % and the temperature difference is large enough. In cold weather an efficiency below 40 % at 90 % rotor speed or more gives an alarm after 5 minutes."),
    "TE3": ("TE3 Temperature after heat recovery", "Supply air temperature after the rotor. Used for the heat recovery efficiency and to check that the heating coil heats."),
    "HC1": ("Heating coil (HC1)", "Hot water coil that heats the supply air after the heat recovery. It is the last heating stage of the supply temperature sequence. Its return water is kept at least at 10 \xb0C at all times to protect it from freezing."),
    "TV1": ("TV1 Heating valve", "Control valve of the heating coil, 0 ... 100 %. It opens after the heat recovery has reached full speed (in the cooling season after the rotor as well). Independent of the sequence it opens to keep the coil return water above 10 \xb0C, and it opens fully when freeze protection trips or the pump fails."),
    "P1": ("P1 Heating coil pump", "Circulation pump of the heating coil. It runs continuously when the outdoor temperature is 9 \xb0C or below, whenever the heating valve is open, and during freeze protection, with a 5 minute run-on. It is exercised once a week for 1 minute. If it does not report running within 30 s of its command the unit stops with a critical alarm."),
    "TE1": ("TE1 Coil return water temperature", "Water temperature leaving the heating coil. It is controlled to at least 10 \xb0C by the heating valve. At 6 \xb0C or below, or on a sensor fault, freeze protection trips: the unit stops, the valve opens fully and an alarm is given; reset is needed."),
    "TE4": ("TE4 Temperature after heating coil", "Supply air temperature after the heating coil. With TE3 it shows the coil's heating effect; if the heating valve is open at least 30 % but the air warms less than 1 K, an alarm is given after 5 minutes."),
    "CC1": ("Cooling coil (CC1)", "Water coil after the heating coil. In the cooling season it cools the supply air with chilled water. When the supplying plant reports warm water in the circuit, it is used in the heating season as a heating stage between the heat recovery and the heating coil."),
    "TV2": ("TV2 Cooling valve", "Control valve of the cooling coil, 0 ... 100 %. In the cooling season it opens when the supply air is too warm, after the heat recovery has done what it can. It closes when the unit stops."),
    "TE5": ("TE5 Temperature after cooling coil", "Supply air temperature after the cooling coil. With TE4 it shows the cooling effect; if the cooling valve is open at least 30 % but the air cools less than 1 K, an alarm is given after 5 minutes."),
    "TF01": ("TF01 Supply fan", "Variable speed fan that blows the treated air into the supply duct. It is started 60 s after the dampers open and its speed (20 ... 60 %) is controlled to hold the supply duct pressure PE1. If it does not report running while commanded, an alarm is given after 15 minutes."),
    "PDE10": ("PDE10 Supply fan flow measurement", "Pressure difference at the supply fan inlet cone. The supply air flow in m3/s is calculated from it with the fan's K factor and shown next to it."),
    "TE2": ("TE2 Supply air temperature", "Temperature of the air going to the rooms; the main control sensor of the unit. Its setpoint follows the extract temperature (21.5 \xb0C at 18 \xb0C extract air down to 16 \xb0C at 23 \xb0C). A deviation of more than 5 K gives an alarm after 5 minutes. 6 \xb0C or below while running trips freeze protection, 50 \xb0C or above trips the unit as a fire risk."),
    "PE1": ("PE1 Supply duct pressure", "Static pressure in the supply duct; the supply fan speed is controlled to its setpoint (80 Pa). A deviation of more than 25 % from the setpoint for 15 minutes gives an alarm."),
    "PE2": ("PE2 Extract duct pressure", "Static pressure (suction) in the extract duct; the extract fan speed is controlled to its setpoint (60 Pa). A deviation of more than 25 % for 15 minutes gives an alarm."),
    "TE7": ("TE7 Extract air temperature", "Temperature of the air returning from the rooms. It sets the supply temperature setpoint, decides on cooling recovery in summer and is the warm side reference of the heat recovery efficiency. 50 \xb0C or above trips the unit as a fire risk."),
    "FLT3": ("Extract filter (PDE2)", "Filter in the extract air that protects the heat recovery wheel. Its condition is supervised by the pressure drop PDE2."),
    "PDE2": ("PDE2 Extract filter pressure drop", "Pressure difference across the extract filter. Alarm \"filter dirty\" after 5 minutes above the limit, which rises with the extract fan speed from 10 Pa at 0 % to 150 Pa at 100 %."),
    "TE8": ("TE8 Exhaust air temperature", "Temperature of the air leaving the heat recovery towards the exhaust. Shown for information; a very low value together with rising PDE4 indicates icing of the wheel."),
    "PF01": ("PF01 Extract fan", "Variable speed fan that draws air from the rooms. It is started 30 s after the dampers open and its speed (20 ... 60 %) is controlled to hold the extract duct pressure PE2. If it does not report running while commanded, an alarm is given after 15 minutes."),
    "PDE20": ("PDE20 Extract fan flow measurement", "Pressure difference at the extract fan inlet cone, from which the extract air flow in m3/s is calculated."),
    "HS10": ("HS10 Extended run button", "Push button in the zone. In automatic mode a press runs the unit for 1 hour beyond the schedule (or extends the current run). It has no effect when the mode selector is Off or Manual."),
    "SB01": ("SB01 Emergency stop", "Stop button on the unit. Pressing it stops the unit at once with a critical alarm. After releasing the button the unit restarts only after an alarm reset."),
    "FA01": ("FA01 Fire alarm", "Contact from the fire alarm panel. On a fire alarm the unit stops at once, dampers close and a critical alarm is given. After the fire panel is reset, the unit needs an alarm reset to restart."),
    "AOM": ("Operating mode selector (AOM)", "Selects how the unit runs: Off (stopped, also at night), Manual (runs continuously) or Auto (time schedule, extended run button and night cooling / heating). Critical alarms stop the unit in every position. The current state is shown as run mode: stopped, normal, night cooling, night heating or alarm stop."),
    "SEASON": ("Season selector", "Selects the temperature sequence: Auto, Heating season or Cooling season. In Auto the unit switches to the cooling season when the previous day's mean outdoor temperature is 11 \xb0C or more and back to heating at 9 \xb0C or less. Night heating is only possible in the heating season, night cooling only in the cooling season."),
    "RESET": ("Alarm reset", "Resets the latched critical alarms (freeze, fire, emergency stop, pump, heat supply, fire risk temperatures). A reset only clears alarms whose cause has gone; the unit then restarts by itself if the mode selector and schedule ask for it."),
}
ROOM_TEXT = ("Three room temperature sensors in the served zone. Their mean (faulty sensors left out) starts and stops night "
             "cooling (above 22 \xb0C / below 19 \xb0C) and night heating (below 18 \xb0C / above 20 \xb0C). Each sensor gives "
             "a fault alarm after 3 minutes.")
for i in (1, 2, 3):
    POP[f"TE10_{i}"] = (f"TE10.{i} Room temperature", ROOM_TEXT)

# --- palette ---------------------------------------------------------------------------------------------------------
W, H = 1600, 900
BG = "#EEF0F3"; PANEL = "#FFFFFF"; EDGE = "#C9CED6"; INK = "#1F2329"; GREY = "#5F6368"; LIGHT = "#BDC1C6"
COLD = "#1A73E8"; COLD_T = "#DCE9FB"; COLD_M = "#7FAEF0"
HOT = "#E8590C"; HOT_T = "#FCE3D3"; HOT_M = "#F39A63"
EXH_T = "#E3E6EA"; EXH_M = "#A3AAB4"
RUNC = "#1E8E3E"; ALM = "#D93025"; AMBER = "#E37400"; SETC = "#0B57D0"
POP_W = 300


class HMI:
    def __init__(self, bench):
        self.g = Graphic(W, H, background=BG)
        self.bench = bench
        self.table = {b[0]: b for b in BINDS + (BENCH if bench else [])}
        self.popups = []                                    # (key, box) for the notes and the fit check

    # --- small helpers -------------------------------------------------------------------------------------------
    def t(self, x, y, s, size=12, bold=False, colour=INK, align="Left"):
        self.g.text(x, y, s, size=size, bold=bold, colour=colour, align=align)

    def v(self, x, y, b, size=14, colour=INK, bold=True, align="Left"):
        _, _, _, dec, unit = self.table[b]
        self.g.value(x, y, b, decimals=dec, unit=unit, size=size, colour=colour, bold=bold, align=align)

    def sp(self, x, y, b, size=13):
        self.v(x, y, b, size=size, colour=SETC)

    def st(self, x, y, b, on, off, size=12, oncol=RUNC, offcol=GREY):
        assert b in self.table, b
        self.g.state(x, y, b, on, off, size=size, on=oncol, off=offcol)

    def mstate(self, x, y, b, words, colours, size=15):
        """Text with one of several words by an integer value (0, 1, 2 ...). Same Text / Bind / Script form as
        Graphic.state; tgml.py has only the two-word form."""
        assert b in self.table, b
        self.g._bind(b)
        w = ",".join(f'"{s}"' for s in words); c = ",".join(f'"{s}"' for s in colours)
        self.g.items.append(
            f'<Text FontFamily="Arial" FontSize="{size}" FontWeight="Bold" Left="{x}" Stroke="{GREY}" Top="{y}">'
            f'<Bind Name="{b}"><Script OnSignalChange="signal"><![CDATA[function signal(evt){{'
            f'var t=evt.getTarget().getParentNode();var i=Math.round(new Number(evt.getValue()));'
            f'var w=[{w}];var c=[{c}];if(i<0||i>={len(words)}){{t.setAttribute("Content","? "+i);return;}}'
            f't.setAttribute("Content",w[i]);t.setAttribute("Stroke",c[i]);}}]]></Script></Bind>--</Text>')

    def lamp(self, x, y, b, d=14, on=RUNC, off=LIGHT):
        assert b in self.table, b
        self.g.lamp(x, y, b, d=d, on=on, off=off)

    def alm(self, x, y, b, d=14):
        """Alarm lamp showing the alarm object's state: A class red and blinking until acknowledged, B red, C amber;
        a ring only = the cause is gone but the alarm is not acknowledged yet."""
        cls = {n: c for n, c, _ in ALARMS}[b]
        self.g.alarm_state(x, y, b, d=d, colour=AMBER if cls == "C" else ALM, blink=(cls == "A"))

    def info(self, x, y, key, prefer=("right", "left", "below", "above")):
        """Info mark; the popup opens to the first side where the whole box lies on the page."""
        title, text = POP[key]
        lines = []
        for para in text.split("\n"):
            lines += textwrap.wrap(para, max(10, int((POP_W - 16) / 5.6))) or [""]
        h = 30 + 15 * len(lines) + 8; d = 16
        for side in list(prefer) + [s for s in ("right", "left", "below", "above") if s not in prefer]:
            bx, by = {"right": (d + 6, -4), "left": (-POP_W - 6, -4), "below": (-POP_W / 2 + d / 2, d + 6),
                      "above": (-POP_W / 2 + d / 2, -h - 6)}[side]
            box = (x + bx, y + by, POP_W, h)
            if box[0] >= 4 and box[1] >= 4 and box[0] + POP_W <= W - 4 and box[1] + h <= H - 4:
                break
        else:
            raise SystemExit(f"popup {key} does not fit on the page")
        self.popups.append((key, side, box))
        self.g.info(x, y, title, text, w=POP_W, side=side)

    def panel(self, x, y, w, h, title, fill=PANEL, edge=EDGE):
        self.g.rect(x, y, w, h, fill=fill, stroke=edge, radius=8)
        self.t(x + 12, y + 8, title, size=14, bold=True)

    # --- symbols, from the library's primitives ------------------------------------------------------------------
    def duct(self, x0, x1, y0, y1, fill, cool=None):
        """cool: the fill in the cooling season (bind SEASON), when the warm and the cold side change places."""
        self.g.rect(x0, y0, x1 - x0, y1 - y0, fill=fill, stroke="None", alt=("SEASON", cool) if cool else None)

    def duct_edges(self, x0, x1, y0, y1):
        self.g.line(x0, y0, x1, y0, "#4A4F57", 2); self.g.line(x0, y1, x1, y1, "#4A4F57", 2)

    def arrow(self, x, y, right, colour, label, ly, cool=None):
        k = 1 if right else -1
        self.g.polygon([(x, y - 14), (x + 22 * k, y), (x, y + 14)], fill=colour, stroke="None", sw=0,
                       bind="SEASON" if cool else None, on=cool, off=colour)
        self.t(x + (4 if right else -4) - (0 if right else 0), ly, label, size=12, bold=True, colour=GREY,
               align="Left" if right else "Right")

    def damper(self, cx, y0, y1, b):
        self.g.rect(cx - 10, y0 - 4, 20, y1 - y0 + 8, fill="#FFFFFF", stroke="#4A4F57", sw=1.5)
        n = 4; step = (y1 - y0) / n
        for i in range(n):
            yc = y0 + step * (i + 0.5)
            self.g.polygon([(cx - 8, yc + 5), (cx - 5, yc + 7), (cx + 8, yc - 5), (cx + 5, yc - 7)],
                           fill=LIGHT, stroke="#4A4F57", sw=1, bind=b, on=RUNC, off=LIGHT)
            self.g.items.append(f'<Ellipse Fill="#4A4F57" Height="3" Left="{cx - 1.5}" Stroke="None" Top="{yc - 1.5}" Width="3"/>')

    def filt(self, cx, y0, y1):
        self.g.rect(cx - 14, y0 - 4, 28, y1 - y0 + 8, fill="#FFFFFF", stroke="#4A4F57", sw=1.5)
        pts = []; y = y0; k = 0
        while y <= y1 + 0.1:
            pts.append(f"{cx - 9 if k % 2 == 0 else cx + 9},{y:.1f}"); y += 8; k += 1
        self.g.path("M" + " L".join(pts), stroke="#6B7280", sw=1.5)

    def coil(self, cx, y0, y1, colour):
        self.g.rect(cx - 16, y0 - 4, 32, y1 - y0 + 8, fill="#FFFFFF", stroke=colour, sw=2)
        xs = [cx - 10, cx - 3, cx + 4, cx + 11]
        d = f"M{xs[0]},{y1 - 4}"
        for i, x in enumerate(xs):
            d += f" L{x},{y0 + 4 if i % 2 == 0 else y1 - 4}"
            if i + 1 < len(xs):
                d += f" L{xs[i + 1]},{y0 + 4 if i % 2 == 0 else y1 - 4}"
        self.g.path(d, stroke=colour, sw=2)

    def sensor(self, x, edge, bad, up=True):
        """Small circle on the duct edge with a stem into the duct; white, red on a sensor fault."""
        k = -1 if up else 1
        self.g.line(x, edge, x, edge - k * 12, "#4A4F57", 2)
        cy = edge + k * 9
        self.lamp(x - 7, cy - 7, bad, d=14, on=ALM, off="#FFFFFF")

    def wheel(self, d=54):
        s = Graphic(d, d); c = d / 2
        s.items.append(f'<Ellipse Fill="#F1F3F4" Height="{d}" Left="0" Stroke="#4A4F57" StrokeWidth="2" Top="0" Width="{d}"/>')
        for k in range(8):
            a = math.pi * k / 4
            s.line(c, c, c + (c - 3) * math.cos(a), c + (c - 3) * math.sin(a), "#6B7280", 2)
        s.items.append(f'<Ellipse Fill="#4A4F57" Height="10" Left="{c - 5}" Stroke="None" Top="{c - 5}" Width="10"/>')
        s.path(f"M{c},{3} A{c - 3},{c - 3} 0 0 1 {d - 3},{c}", stroke=HOT, sw=3)
        return s

    def vpipe(self, x, y0, y1, colour, b, up):
        self.g.line(x, y0, x, y1, colour, 6)
        L = y1 - y0
        self.g.flow(x - 2, y0, -L if up else L, b, vertical=True, colour="#FFFFFF", seconds=1.0, thick=4)

    def hpipe(self, x0, x1, y, colour, b, right):
        self.g.line(x0, y, x1, y, colour, 6)
        L = x1 - x0
        self.g.flow(x0, y - 2, L if right else -L, b, colour="#FFFFFF", seconds=1.0, thick=4)

    def vvalve(self, x, y, colour, right=False):
        """Two-way valve on a vertical pipe, actuator to the left (or to the right)."""
        s = 12; k = -1 if right else 1
        self.g.polygon([(x - s * 0.7, y - s), (x, y), (x + s * 0.7, y - s)], fill="#FFFFFF", stroke=colour, sw=2)
        self.g.polygon([(x - s * 0.7, y + s), (x, y), (x + s * 0.7, y + s)], fill="#FFFFFF", stroke=colour, sw=2)
        self.g.line(x, y, x - 18 * k, y, "#4A4F57", 2)
        self.g.rect(x - 30 if k > 0 else x + 18, y - 9, 12, 18, fill="#E8EAED", stroke="#4A4F57")

    def valve(self, x, y, colour):
        s = 13
        self.g.polygon([(x - s, y - s * 0.7), (x, y), (x - s, y + s * 0.7)], fill="#FFFFFF", stroke=colour, sw=2)
        self.g.polygon([(x + s, y - s * 0.7), (x, y), (x + s, y + s * 0.7)], fill="#FFFFFF", stroke=colour, sw=2)
        self.g.line(x, y, x, y - 18, "#4A4F57", 2)
        self.g.rect(x - 9, y - 30, 18, 12, fill="#E8EAED", stroke="#4A4F57")

    # --- the page --------------------------------------------------------------------------------------------------
    def build(self):
        g = self.g
        EX0, EX1 = 198, 262; EXC = (EX0 + EX1) / 2           # extract / exhaust duct (top), air right to left
        SU0, SU1 = 384, 448; SUC = (SU0 + SU1) / 2           # outdoor / supply duct (bottom), air left to right
        X_FZ, X_TE6, X_F1, X_F2, X_SC3, X_TE3, X_HC, X_TE4, X_CC, X_TE5, X_TF, X_TE2, X_PE1 = \
            115, 160, 215, 302, 410, 490, 552, 635, 712, 780, 850, 975, 1080
        X_PF, X_TE8, X_F3, X_TE7, X_PE2 = 222, 318, 560, 975, 1080
        L, R = 36, 1182                                      # duct ends

        # header
        g.rect(0, 0, W, 64, fill="#263040", stroke="None")
        self.t(20, 9, "AHU01", size=24, bold=True, colour="#FFFFFF")
        self.t(20, 41, "Supply and extract air handling unit", size=12, colour="#C5CBD3")
        cols = [(330, "Run mode"), (500, "Mode selector"), (660, "Season selector"), (830, "Season in use"),
                (990, "Night cooling"), (1105, "Night heating"), (1220, "Cooling coil water")]
        for x, lab in cols:
            self.t(x, 10, lab, size=11, colour="#AEB6C1")
        self.mstate(330, 30, "RUN_MODE", ["Stopped", "Normal", "Night cooling", "Night heating", "Alarm stop"],
                    ["#C5CBD3", "#5BD17F", "#8AB4F8", "#F6AE6B", "#FF8A80"])
        self.mstate(500, 30, "AOM", ["Off", "Manual", "Auto"], ["#FF8A80", "#FDD663", "#5BD17F"])
        self.info(560, 30, "AOM", prefer=("below",))
        g.step_button(584, 27, "AOM", -1, "-", w=20, h=20, lo=0, hi=2); g.step_button(607, 27, "AOM", 1, "+", w=20, h=20, lo=0, hi=2)
        self.mstate(660, 30, "SEASON_SEL", ["Auto", "Heating", "Cooling"], ["#5BD17F", "#F6AE6B", "#8AB4F8"])
        self.info(740, 30, "SEASON", prefer=("below",))
        g.step_button(764, 27, "SEASON_SEL", -1, "-", w=20, h=20, lo=0, hi=2); g.step_button(787, 27, "SEASON_SEL", 1, "+", w=20, h=20, lo=0, hi=2)
        self.st(830, 31, "SEASON", "Cooling", "Heating", size=15, oncol="#8AB4F8", offcol="#F6AE6B")
        self.st(990, 31, "NIGHT_COOL", "ACTIVE", "off", size=15, oncol="#8AB4F8", offcol="#C5CBD3")
        self.st(1105, 31, "NIGHT_HEAT", "ACTIVE", "off", size=15, oncol="#F6AE6B", offcol="#C5CBD3")
        self.st(1220, 31, "HEAT_MODE", "warm", "chilled", size=15, oncol="#F6AE6B", offcol="#8AB4F8")
        g.alarm_lamp(1318, 21, "CRIT", d=22, colour=ALM)
        self.t(1346, 10, "Critical alarm", size=11, colour="#AEB6C1")
        self.st(1346, 31, "CRIT", "UNIT STOPPED", "none", size=15, oncol="#FF8A80", offcol="#C5CBD3")
        g.step_button(1490, 20, "RESET", 1, "Reset", w=72, h=26, lo=0, hi=1)
        self.info(1568, 25, "RESET", prefer=("left",))

        # unit casing
        g.rect(84, EX0 - 36, 832, SU1 - EX0 + 72, fill="#F8F9FA", stroke="#8E959E", sw=2, radius=10)

        # ducts with the air colour of each section, then the moving marks, then the parts on top
        # heating season: cold outdoor air, warm supply and extract. Cooling season (SEASON = 1): the colours change places.
        self.duct(L, X_SC3, EX0, EX1, EXH_T); self.duct(X_SC3, R, EX0, EX1, HOT_T, COLD_T)
        self.duct(L, X_SC3, SU0, SU1, COLD_T, HOT_T); self.duct(X_SC3, R, SU0, SU1, HOT_T, COLD_T)
        # air: thin streaks drifting along the ducts while the unit runs
        g.airflow(L + 24, EX0 + 8, -(X_SC3 - L - 24), EX1 - EX0 - 16, "RUN", colour=EXH_M, seconds=1.6)
        g.airflow(X_SC3, EX0 + 8, -(R - 24 - X_SC3), EX1 - EX0 - 16, "RUN", colour=HOT_M, seconds=1.6, alt=("SEASON", COLD_M))
        g.airflow(L, SU0 + 8, X_SC3 - L, SU1 - SU0 - 16, "RUN", colour=COLD_M, seconds=1.6, alt=("SEASON", HOT_M))
        g.airflow(X_SC3, SU0 + 8, R - 24 - X_SC3, SU1 - SU0 - 16, "RUN", colour=HOT_M, seconds=1.6, alt=("SEASON", COLD_M))
        self.duct_edges(L, R, EX0, EX1); self.duct_edges(L, R, SU0, SU1)
        self.arrow(L - 2, EXC, False, EXH_M, "", 0)
        self.t(12, EX0 - 30, "Exhaust air", size=12, bold=True, colour=GREY)
        self.arrow(R - 22, EXC, False, HOT_M, "", 0, COLD_M)
        self.t(R, EX0 - 30, "Extract air", size=12, bold=True, colour=GREY, align="Right")
        self.arrow(L - 26, SUC, True, COLD_M, "", 0, HOT_M)
        self.t(12, SU0 - 30, "Outdoor air", size=12, bold=True, colour=GREY)
        self.arrow(R - 22, SUC, True, HOT_M, "", 0, COLD_M)
        self.t(R, SU1 + 8, "Supply air", size=12, bold=True, colour=GREY, align="Right")
        self.t(R, SU1 + 24, "to the zone", size=11, colour=GREY, align="Right")
        self.t(R, EX0 - 14, "from the zone", size=11, colour=GREY, align="Right")

        # --- extract path, right to left: PE2, TE7, FLT3, SC3 (PDE4), TE8, PF01 (PDE20), FZ02 ---
        self.psensor(X_PE2, EX0, up=True)
        self.t(X_PE2 - 30, 92, "PE2", size=13, bold=True); self.info(X_PE2 + 2, 92, "PE2", prefer=("left", "below"))
        self.v(X_PE2 - 30, 110, "PE2"); self.t(X_PE2 - 30, 131, "SP", size=11, colour=GREY); self.v(X_PE2 - 12, 129, "PE2_SP", size=12, bold=False)
        self.alm(X_PE2 + 40, 112, "Exhaust_Pres_Alm", d=12)

        self.sensor(X_TE7, EX0, "TE7_BAD", up=True)
        self.t(X_TE7 - 30, 110, "TE7", size=13, bold=True); self.info(X_TE7 + 2, 110, "TE7", prefer=("below", "left"))
        self.v(X_TE7 - 30, 128, "TE7")

        self.filt(X_F3, EX0, EX1)
        self.t(X_F3 - 26, 92, "FLT3", size=13, bold=True); self.info(X_F3 + 14, 92, "FLT3", prefer=("below", "right"))
        self.t(X_F3 - 26, 112, "PDE2", size=11, colour=GREY); self.info(X_F3 + 14, 111, "PDE2", prefer=("below", "right"))
        self.v(X_F3 - 26, 128, "PDE2", size=13); self.alm(X_F3 + 36, 131, "PDE2_Alm", d=12)
        self.t(X_F3 - 26, 147, "Extract filter", size=10, colour=GREY)

        # rotor across both ducts, wheel symbol turning between them
        # rotor seen from the side, across both ducts: its lines travel while the drive runs
        g.rect(X_SC3 - 26, EX0 - 10, 52, SU1 - EX0 + 20, fill="#ECEFF1", stroke="#4A4F57", sw=2, radius=8)
        g.drum(X_SC3 - 22, EX0 - 4, 44, SU1 - EX0 + 8, "SC3_CMD", seconds=1.2, spacing=9, colour=HOT_M, alt=("SEASON", COLD_M))
        g.line(X_SC3 - 26, (EX1 + SU0) / 2, X_SC3 + 26, (EX1 + SU0) / 2, "#4A4F57", 2)      # shaft line between the ducts
        self.t(X_SC3 - 40, 86, "PDE4", size=13, bold=True); self.info(X_SC3 + 4, 86, "PDE4", prefer=("below", "right"))
        self.v(X_SC3 - 40, 104, "PDE4", size=13)
        self.t(X_SC3 - 40, 124, "limit", size=11, colour=GREY); self.v(X_SC3 - 8, 122, "PDE4_SP", size=12, bold=False)
        self.st(X_SC3 - 40, 142, "FROST", "FROST LIMIT", "no frost", size=11, oncol=COLD, offcol=GREY)

        self.sensor(X_TE8, EX0, "TE8_BAD", up=True)
        self.t(X_TE8 - 24, 110, "TE8", size=13, bold=True); self.info(X_TE8 + 8, 110, "TE8", prefer=("below", "right"))
        self.v(X_TE8 - 24, 128, "TE8")

        g.fan(X_PF - 28, EXC - 28, "PF01_FDB", d=56)
        self.t(X_PF - 52, 74, "PF01", size=13, bold=True); self.info(X_PF - 12, 74, "PF01", prefer=("below", "right"))
        self.v(X_PF - 52, 91, "PF01", size=14)
        self.lamp(X_PF - 4, 94, "PF01_FDB", d=12); self.t(X_PF + 11, 93, "run", size=11, colour=GREY)
        self.alm(X_PF + 36, 94, "PF01_Alm", d=12)
        self.st(X_PF - 52, 110, "PF01_CMD", "start cmd ON", "start cmd off", size=11)
        self.t(X_PF - 52, 127, "PDE20", size=11, colour=GREY); self.info(X_PF - 12, 126, "PDE20", prefer=("below", "right"))
        self.v(X_PF + 10, 126, "PDE20", size=12, bold=False)
        self.v(X_PF - 52, 143, "Q_EXH", size=12)

        self.damper(X_FZ, EX0, EX1, "FZ02")
        self.t(X_FZ - 22, 120, "FZ02", size=13, bold=True); self.info(X_FZ + 16, 120, "FZ02", prefer=("below", "right"))
        self.st(X_FZ - 22, 138, "FZ02", "OPEN", "CLOSED", size=11)

        # --- supply path, left to right: FZ01, TE6, FLT1 (PDE3), FLT2 (PDE1), SC3, TE3, HC1, TE4, CC1, TE5, TF01, TE2, PE1
        self.damper(X_FZ, SU0, SU1, "FZ01")
        self.t(X_FZ - 22, 490, "FZ01", size=13, bold=True); self.info(X_FZ + 16, 490, "FZ01", prefer=("right", "above"))
        self.st(X_FZ - 22, 508, "FZ01", "OPEN", "CLOSED", size=11)

        self.gsensor(X_TE6, SU0, "TE6", "TE6_BAD")

        for x, tag, dp, a, label in ((X_F1, "FLT1", "PDE3", "PDE3_Alm", "Filter 1"), (X_F2, "FLT2", "PDE1", "PDE1_Alm", "Filter 2")):
            self.filt(x, SU0, SU1)
            self.t(x - 22, 490, tag, size=13, bold=True); self.info(x + 16, 490, tag, prefer=("right", "above"))
            self.t(x - 22, 510, dp, size=11, colour=GREY); self.info(x + 16, 509, dp, prefer=("right", "above"))
            self.v(x - 22, 526, dp, size=13); self.alm(x + 36, 529, a, d=12)

        # SC3 values below the supply duct
        sx = X_SC3 - 34
        self.t(sx, 492, "SC3", size=13, bold=True); self.info(sx + 32, 492, "SC3", prefer=("right", "above"))
        self.v(sx, 510, "SC3", size=14); self.alm(sx + 50, 513, "HRU_Alm", d=12)
        self.st(sx, 530, "SC3_CMD", "running", "stopped", size=11)
        self.st(sx, 546, "SC3_OK", "drive ok", "DRIVE FAULT", size=11, oncol=GREY, offcol=ALM)
        self.t(sx, 566, "Efficiency", size=11, colour=GREY); self.info(sx + 58, 565, "EFF", prefer=("right", "above"))
        self.v(sx, 582, "HRU_EFF", size=13); self.alm(sx + 50, 585, "HRU_Efficiency_Alm", d=12)

        self.gsensor(X_TE3, SU0, "TE3", "TE3_BAD")

        # heating coil and its water circuit (shunt group): two straight pipes from below. Counterflow: the water enters
        # on the side where the air leaves (right), pump P1 on it; it returns on the side where the air enters (left)
        # past TE1, and the control valve TV1 sits on the return. The bypass between them lets P1 circulate water
        # through the coil when TV1 is closed. No bends: the running marks of a pipe cannot go round a corner.
        self.coil(X_HC, SU0, SU1, HOT)
        xs, xr = X_HC + 12, X_HC - 12; yb = 700
        # above the bypass the water circulates whenever P1 runs; below it only while TV1 is open
        yby = 602
        self.vpipe(xs, yby, yb, HOT, "TV1", up=True); self.vpipe(xr, yby, yb, COLD_M, "TV1", up=False)
        self.vpipe(xs, SU1 + 4, yby, HOT, "P1_FDB", up=True); self.vpipe(xr, SU1 + 4, yby, COLD_M, "P1_FDB", up=False)
        self.t(xs + 8, yb - 6, "heating water in", size=10, colour=GREY); self.t(xr - 8, yb - 6, "return", size=10, colour=GREY, align="Right")
        self.t(xs + 10, 490, "HC1", size=13, bold=True); self.info(xs + 42, 490, "HC1", prefer=("right", "above"))
        # supply: pump
        g.pump(xs - 13, 546, "P1_FDB", d=26, direction="up")
        self.t(xs + 22, 542, "P1", size=13, bold=True); self.info(xs + 44, 542, "P1", prefer=("right", "above"))
        self.st(xs + 22, 560, "P1_CMD", "cmd", "", size=11)
        self.alm(xs + 54, 561, "P1_Alm", d=12)
        # bypass with its check valve, return -> pump suction
        self.hpipe(xr, xs, yby, COLD_M, "P1_FDB", right=True)
        g.polygon([(X_HC - 5, 596), (X_HC + 5, 602), (X_HC - 5, 608)], fill="#FFFFFF", stroke="#4A4F57", sw=1.2)
        # return: TE1 at the coil outlet, then the bypass, then TV1
        bx = xr - 78
        g.line(xr - 8, 520, xr, 520, "#4A4F57", 2)
        self.lamp(xr - 22, 513, "TE1_BAD", d=14, on=ALM, off="#FFFFFF")
        self.t(bx, 498, "TE1", size=13, bold=True); self.info(bx + 28, 498, "TE1", prefer=("left", "above"))
        self.v(bx, 516, "TE1", size=13)
        self.st(bx, 536, "FREEZE", "FREEZE TRIP", "no freeze", size=11, oncol=ALM)
        self.vvalve(xr, 645, HOT)
        self.t(xr - 84, 628, "TV1", size=13, bold=True); self.info(xr - 52, 628, "TV1", prefer=("left", "above"))
        self.v(xr - 84, 646, "TV1", size=13)

        self.gsensor(X_TE4, SU0, "TE4", "TE4_BAD")

        # cooling coil: chilled water straight up on the air leaving side, return straight down through TV2
        self.coil(X_CC, SU0, SU1, COLD)
        cs, cr = X_CC + 12, X_CC - 12
        self.vpipe(cs, SU1 + 4, yb, COLD, "TV2", up=True)
        self.vpipe(cr, SU1 + 4, yb, COLD_M, "TV2", up=False)
        self.t(cs + 8, yb - 6, "chilled water in", size=10, colour=GREY); self.t(cr - 8, yb - 6, "return", size=10, colour=GREY, align="Right")
        self.vvalve(cr, 645, COLD)
        self.t(cr - 84, 628, "TV2", size=13, bold=True); self.info(cr - 52, 628, "TV2", prefer=("left", "above"))
        self.v(cr - 84, 646, "TV2", size=13)
        self.t(cs + 10, 490, "CC1", size=13, bold=True); self.info(cs + 42, 490, "CC1", prefer=("right", "above"))

        self.gsensor(X_TE5, SU0, "TE5", "TE5_BAD")

        g.fan(X_TF - 28, SUC - 28, "TF01_FDB", d=56)
        fx = X_TF - 22
        self.t(fx, 490, "TF01", size=13, bold=True); self.info(fx + 40, 490, "TF01", prefer=("right", "above"))
        self.v(fx, 508, "TF01", size=14)
        self.lamp(fx + 48, 511, "TF01_FDB", d=12); self.t(fx + 63, 510, "run", size=11, colour=GREY)
        self.alm(fx + 88, 511, "TF01_Alm", d=12)
        self.st(fx, 528, "TF01_CMD", "start cmd ON", "start cmd off", size=11)
        self.t(fx, 546, "PDE10", size=11, colour=GREY); self.info(fx + 40, 545, "PDE10", prefer=("right", "above"))
        self.v(fx + 62, 545, "PDE10", size=12, bold=False)
        self.v(fx, 562, "Q_SUP", size=12)

        # TE2 with the setpoint in use and the deviation alarm, PE1 with its setpoint
        self.gsensor(X_TE2, SU0, "TE2", "TE2_BAD", sp=("ACT_SP", "Supply_Temp_Alm"))
        self.psensor(X_PE1, SU0, up=True)
        self.t(X_PE1 - 30, 296, "PE1", size=13, bold=True); self.info(X_PE1 + 2, 296, "PE1", prefer=("left", "above"))
        self.v(X_PE1 - 30, 314, "PE1"); self.t(X_PE1 - 30, 335, "SP", size=11, colour=GREY); self.v(X_PE1 - 12, 333, "PE1_SP", size=12, bold=False)
        self.alm(X_PE1 + 40, 317, "Supply_Pres_Alm", d=12)

        # --- right column: setpoints and alarms ---
        self.setpoints(1196, 76)
        self.alarms(1196, 382)
        # --- bottom: zone, outdoor / safety, test bench ---
        self.zone(20, 724)
        self.outdoor(372, 724)
        if self.bench:
            self.bench_panel(632, 724)
        else:
            self.t(632, 870, "Blue values are setpoints: click to change.", size=11, colour=GREY)

    def gsensor(self, x, edge, b, bad, sp=None):
        """Supply temperature sensor on the top edge of the supply duct, tag and value in the gap above."""
        self.sensor(x, edge, bad, up=True)
        top = 312 if sp is None else 296
        self.t(x - 24, top, b, size=13, bold=True); self.info(x + 6, top, b, prefer=("above", "right", "left"))
        self.v(x - 24, top + 18, b)
        if sp:
            self.t(x - 24, top + 39, "SP", size=11, colour=GREY); self.v(x - 6, top + 37, sp[0], size=12, bold=False)
            self.alm(x + 48, top + 21, sp[1], d=12)

    def psensor(self, x, edge, up=True):
        """Pressure sensor: small square tapping on the duct edge."""
        k = -1 if up else 1
        self.g.line(x, edge, x, edge + k * 8, "#4A4F57", 2)
        self.g.rect(x - 6, edge + k * 8 - (12 if up else 0), 12, 12, fill="#FFFFFF", stroke="#4A4F57", sw=1.5)

    def setpoints(self, x, y):
        self.panel(x, y, 392, 296, "Setpoints")
        self.t(x + 380, y + 11, "click a blue value to change", size=10, colour=GREY, align="Right")
        rows = [("Supply duct pressure", "PE1_SET", 10, 20, 400), ("Extract duct pressure", "PE2_SET", 10, 20, 400),
                ("Supply air at cold extract (pt 1)", "SP_Y1", 0.5, 10, 35), ("  ... at extract air", "ET_X1", None, 0, 0),
                ("Supply air at warm extract (pt 2)", "SP_Y2", None, 0, 0), ("  ... at extract air", "ET_X2", None, 0, 0),
                ("Coil return water minimum", "COIL_ST", None, 0, 0), ("Freeze protection limit", "FREEZE_SP", None, 0, 0),
                ("Rotor speed limit in frost", "FROST_LIM", None, 0, 0)]
        for i, (lab, b, step, lo, hi) in enumerate(rows):
            yy = y + 38 + i * 26
            self.t(x + 12, yy + 2, lab, size=12)
            self.sp(x + 230, yy, b, size=14)
            if step:
                self.g.step_button(x + 310, yy - 2, b, -step, "-", lo=lo, hi=hi)
                self.g.step_button(x + 342, yy - 2, b, step, "+", lo=lo, hi=hi)
        yy = y + 38 + len(rows) * 26 + 4
        self.g.line(x + 12, yy - 4, x + 380, yy - 4, EDGE, 1)
        self.t(x + 12, yy + 2, "Supply setpoint in use", size=12, colour=GREY); self.v(x + 230, yy, "ACT_SP", size=14)

    def alarms(self, x, y):
        self.panel(x, y, 392, 508, "Alarms")
        self.t(x + 380, y + 11, "A blinks (unit stopped)  B red  C amber", size=10, colour=GREY, align="Right")
        n = (len(ALARMS) + 1) // 2
        for i, (name, cls, label) in enumerate(ALARMS):
            col, row = divmod(i, n)
            xx, yy = x + 12 + col * 192, y + 38 + row * 27
            self.alm(xx, yy, name, d=15)
            self.t(xx + 21, yy + 1, label, size=12, colour=INK if cls == "A" else INK)
            self.t(xx + 176, yy + 2, cls, size=10, colour=GREY, align="Right")

    def zone(self, x, y):
        self.panel(x, y, 342, 166, "Zone")
        for i in (1, 2, 3):
            yy = y + 36 + (i - 1) * 24
            b = f"TE10_{i}"
            self.lamp(x + 12, yy + 1, f"{b}_BAD", d=14, on=ALM, off="#FFFFFF")
            self.t(x + 32, yy + 1, f"TE10.{i}", size=13, bold=True); self.v(x + 96, yy, b)
            self.info(x + 168, yy, b, prefer=("above", "right"))
            self.room_popup(x + 190, yy, i)
        self.t(x + 220, y + 36, "Room mean", size=12, colour=GREY); self.v(x + 220, y + 52, "ROOM_AVG", size=16)
        yy = y + 112
        self.g.line(x + 12, yy - 6, x + 330, yy - 6, EDGE, 1)
        self.t(x + 12, yy, "HS10", size=13, bold=True); self.info(x + 170, yy, "HS10", prefer=("above", "right"))
        self.st(x + 80, yy + 1, "HS10", "PRESSED", "released", size=12)
        self.t(x + 12, yy + 24, "Extended run", size=12, colour=GREY)
        self.st(x + 112, yy + 24, "HS10_EXT", "ACTIVE", "off", size=12)

    def room_popup(self, x, y, i):
        """Green "T" mark: opens the room sensor faceplate (examples/room-sensor/roomface.py) with this sensor's
        live temperature, the room mean, its fault flag and its alarm lamp. No new bind names: all four are on
        the page already."""
        b = f"TE10_{i}"; kw = dict(mean="ROOM_AVG", bad=f"{b}_BAD", alarm=f"{b}_Alm")
        for n in (b, *kw.values()):
            assert n in self.table, n
        h = roomface.height(**kw)
        box = self.g.popup(x, y, roomface.W, h, lambda p, ox, oy: roomface.face(p, ox, oy, f"TE10.{i}", b, **kw),
                           side="above", mark="T")
        assert box[0] >= 4 and box[1] >= 4 and box[0] + box[2] <= W - 4 and box[1] + box[3] <= H - 4, box
        self.popups.append((f"{b} room sensor", "above", box))

    def outdoor(self, x, y):
        self.panel(x, y, 250, 166, "Outdoor and safety")
        self.lamp(x + 12, y + 37, "TE00_BAD", d=14, on=ALM, off="#FFFFFF")
        self.t(x + 32, y + 37, "TE00", size=13, bold=True); self.info(x + 72, y + 36, "TE00", prefer=("above", "right"))
        self.v(x + 96, y + 36, "TE00", size=16)
        self.t(x + 32, y + 60, "yesterday's mean", size=11, colour=GREY); self.v(x + 140, y + 59, "OT_DAY", size=12, bold=False)
        self.g.line(x + 12, y + 82, x + 238, y + 82, EDGE, 1)
        self.t(x + 12, y + 92, "SB01", size=13, bold=True); self.info(x + 52, y + 91, "SB01", prefer=("above", "right"))
        self.st(x + 80, y + 93, "SB01", "normal", "PRESSED", size=12, oncol=GREY, offcol=ALM)
        self.t(x + 12, y + 118, "FA01", size=13, bold=True); self.info(x + 52, y + 117, "FA01", prefer=("above", "right"))
        self.st(x + 80, y + 119, "FA01", "normal", "FIRE ALARM", size=12, oncol=GREY, offcol=ALM)
        self.t(x + 12, y + 142, "Emergency stop / fire panel", size=10, colour=GREY)

    def bench_panel(self, x, y):
        self.panel(x, y, 552, 166, "Test bench (plant simulation)", fill="#FFF8E1", edge="#F2B400")
        self.t(x + 540, y + 11, "separate program, leave out on a real unit", size=10, colour=GREY, align="Right")
        self.t(x + 12, y + 38, "Outdoor temperature", size=12)
        for k, (step, lab) in enumerate(((-5, "-5"), (-1, "-1"))):
            self.g.step_button(x + 12 + k * 32, y + 56, "B_OT", step, lab, w=28, lo=-40, hi=40)
        self.v(x + 80, y + 58, "B_OT", size=16, colour=SETC)
        for k, (step, lab) in enumerate(((1, "+1"), (5, "+5"))):
            self.g.step_button(x + 156 + k * 32, y + 56, "B_OT", step, lab, w=28, lo=-40, hi=40)
        self.t(x + 12, y + 94, "Heating water supply (freeze test)", size=12)
        self.g.step_button(x + 12, y + 112, "B_HWT", -5, "-5", w=28, lo=0, hi=90)
        self.v(x + 48, y + 114, "B_HWT", size=16, colour=SETC)
        self.g.step_button(x + 110, y + 112, "B_HWT", 5, "+5", w=28, lo=0, hi=90)
        sw = [("B_FIRE", "Fire alarm", "FIRE"), ("B_ESTOP", "Emergency stop", "PRESSED"), ("B_P1F", "Pump P1 fails", "FAULT"),
              ("B_SC3F", "Rotor drive fault", "FAULT"), ("B_TF01F", "Supply fan trips", "FAULT"), ("B_ICE", "Rotor icing", "ICING")]
        for i, (b, lab, on) in enumerate(sw):
            col, row = divmod(i, 3)
            xx, yy = x + 250 + col * 150, y + 38 + row * 40
            self.t(xx, yy, lab, size=11, colour=GREY)
            self.g.step_button(xx, yy + 16, b, -1, "0", w=22, h=20, lo=0, hi=1)
            self.g.step_button(xx + 26, yy + 16, b, 1, "1", w=22, h=20, lo=0, hi=1)
            self.st(xx + 54, yy + 18, b, on, "off", size=12, oncol=ALM)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", action="store_true", help="add the test bench panel (TEST/... of the simulation)")
    ap.add_argument("-o", "--out", default="AHU01-HMI.tgml")
    a = ap.parse_args()
    h = HMI(a.bench)
    h.build()
    g = h.g
    used = set(g.binds)
    table = h.table
    missing = sorted(used - set(table)); unused = sorted(set(table) - used)
    assert not missing and not unused, ("missing", missing, "unused", unused)
    out = a.out if os.path.isabs(a.out) else os.path.join(HERE, a.out)
    g.save(out)
    binds = {"controller": {b[0]: b[1] for b in BINDS}, "bench": {b[0]: b[1] for b in BENCH} if a.bench else {}}
    with open(os.path.join(os.path.dirname(out), "hmi_binds.json"), "w") as f:
        json.dump(binds, f, indent=1)
    # checks: well-formed, only known elements
    import xml.etree.ElementTree as ET
    root = ET.parse(out).getroot()
    allowed = {"Tgml", "Rectangle", "Line", "Ellipse", "Polygon", "Path", "Text", "Component", "Group", "Bind",
               "ConvertValue", "Script", "Animate", "Rotate", "Translate"}
    tags = {e.tag for e in root.iter()}
    assert tags <= allowed, tags - allowed
    print(f"{os.path.basename(out)}: {W} x {H}, {len(g.items) + len(g.top)} top-level elements, "
          f"{sum(1 for _ in root.iter())} XML elements, {len(g.binds)} binds, {len(h.popups)} popups")
    if os.environ.get("AHU01_POPUPS"):                       # popup sides and boxes, for the layout check
        with open(os.environ["AHU01_POPUPS"], "w") as f:
            json.dump(h.popups, f)


if __name__ == "__main__":
    main()
