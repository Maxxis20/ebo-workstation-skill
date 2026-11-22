#!/usr/bin/env python3
"""make_fuxa.py: FUXA view of AHU01, fed by the MQTT topics that make_mqtt.py has EBO publish.

    python3 make_fuxa.py ['/Server 1'] [AHU01]     -> AHU01.fuxa.json (load: ebo.sh fuxa AHU01.fuxa.json)

One MQTT device on the broker of the EBO machine (mqtt://127.0.0.1:1883), one raw tag per published point (tag name = bind
name of the EBO graphic, address = topic), one view "AHU01" drawn like the EBO graphic (AHU01-HMI_preview.png):
header with run mode, selectors, season, night modes, critical alarm; extract / exhaust duct on top flowing right
to left, outdoor / supply duct below flowing left to right, rotor SC3 across both, filters, heating coil HC1 with
pump P1 on the supply pipe and valve TV1 on the return, cooling coil CC1 with TV2 on the return, fans, dampers,
sensors with live values; alarm lamps on the right; zone, outdoor and setpoints-in-use panels below.

FUXA shows numbers and lamps only (findings, section MQTT): a multi-state value (run mode, selectors) is its
number with the meaning written beside it, a state is a lamp, units go into the labels. Read-only: no setpoint
can be changed from this view (the MQTT direction back into EBO is not set up).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.dont_write_bytecode = True                       # make_mqtt is imported: no __pycache__ beside the example
from fuxa import Fuxa
import make_mqtt

W, H = 1540, 900
INK, MUTED, WHITE = "#202124", "#5f6368", "#ffffff"
LIVE, SPC = "#0b57d0", "#188038"                      # live values blue, setpoints in use green
GREY, GREEN, RED, AMBER, ORANGE, BLUE = "#d5d9de", "#34a853", "#d93025", "#f9ab00", "#f28c38", "#4f8fe8"
COLD, WARM, EXH = "#dbeafe", "#fde4d3", "#e8eaed"     # duct fills: outdoor, after the rotor / extract, exhaust
DEG = "\xb0C"


def build(server="/Server 1", folder="AHU01"):
    pts = make_mqtt.points(server, folder)
    f = Fuxa("AHU01", width=W, height=H, background="#eef0f3", title="AHU01 over MQTT")
    t = {p["tag"]: f.tag(p["tag"], p["topic"]) for p in pts}
    used = set()

    def T(tag):
        used.add(tag)
        return t[tag]

    def num(x, y, label, tag, digits=1, size=16, fill=LIVE, lsize=11, lfill=MUTED):
        """Label above, live number below (y = baseline of the label)."""
        f.text(x, y, label, lsize, fill=lfill)
        f.value(x, y + size + 4, T(tag), digits=digits, size=size, fill=fill)

    def lamp(x, y, label, tag, on=GREEN, r=7, size=11, fill=INK, **kw):
        f.lamp(x + r, y - 4, T(tag), on=on, r=r, **kw)
        f.text(x + 2 * r + 6, y, label, size, fill=fill)

    # ---- header ---------------------------------------------------------------------------------------------------
    f.box(0, 0, W, 72, fill="#263238", stroke="#263238", radius=0)
    f.text(16, 32, "AHU01", 24, "bold", WHITE)
    f.text(16, 56, "Supply and extract air handling unit, live from EBO over MQTT", 12, fill="#b0bec5")
    hl = lambda x, s: f.text(x, 18, s, 11, fill="#b0bec5")
    leg = lambda x, s: f.text(x, 64, s, 10, fill="#90a4ae")
    hl(440, "Run mode"); f.lamp(450, 40, T("RUN_MODE"), r=8, stroke="#90a4ae",
                                ranges=[(0, 0, GREY), (1, 1, GREEN), (2, 2, BLUE), (3, 3, ORANGE), (4, 4, RED)])
    f.value(466, 47, t["RUN_MODE"], digits=0, size=18, fill=WHITE)
    leg(440, "0 stop 1 normal 2 night cool 3 night heat 4 alarm")
    hl(670, "Mode selector"); f.value(670, 47, T("AOM"), digits=0, size=18, fill=WHITE); leg(670, "0 off 1 manual 2 auto")
    hl(800, "Season selector"); f.value(800, 47, T("SEASON_SEL"), digits=0, size=18, fill=WHITE); leg(800, "0 auto 1 heat 2 cool")
    hl(930, "Season in use"); f.lamp(940, 40, T("SEASON"), r=8, stroke="#90a4ae", ranges=[(0, 0, ORANGE), (1, 1, BLUE)])
    leg(930, "orange heat, blue cool")
    hl(1060, "Night cooling"); f.lamp(1070, 40, T("NIGHT_COOL"), on=BLUE, r=8, stroke="#90a4ae")
    hl(1150, "Night heating"); f.lamp(1160, 40, T("NIGHT_HEAT"), on=ORANGE, r=8, stroke="#90a4ae")
    hl(1240, "Cooling coil water"); f.lamp(1250, 40, T("HEAT_MODE"), r=8, stroke="#90a4ae", ranges=[(0, 0, BLUE), (1, 1, ORANGE)])
    leg(1240, "blue chilled, orange warm")
    hl(1370, "Running"); f.lamp(1380, 40, T("RUN"), r=8, stroke="#90a4ae")
    hl(1440, "Critical alarm"); f.lamp(1452, 40, T("CRIT"), on=RED, r=10, stroke="#90a4ae")

    # ---- schematic --------------------------------------------------------------------------------------------------
    f.box(10, 82, 1150, 640, fill=WHITE, stroke="#c4c9cf")
    f.box(90, 180, 830, 320, fill="#f6f7f9", stroke="#9aa0a6", radius=10)                  # unit casing
    EX0, EX1, SU0, SU1, RX0, RX1 = 210, 262, 420, 472, 380, 420                              # duct edges, rotor x
    for y0, y1, left, right in ((EX0, EX1, EXH, WARM), (SU0, SU1, COLD, WARM)):
        f.box(40, y0, RX0 - 40, y1 - y0, fill=left, stroke="none", radius=0)
        f.box(RX1, y0, 1140 - RX1, y1 - y0, fill=right, stroke="none", radius=0)
        f.line(40, y0, 1140, y0, MUTED, 2); f.line(40, y1, 1140, y1, MUTED, 2)
    for x in (165, 470, 760, 940, 1030):                                                    # direction marks
        f.polyline([(x + 6, EX0 + 16), (x - 4, EX0 + 26), (x + 6, EX0 + 36)], "#9aa0a6", 2)
        f.polyline([(x - 6, SU0 + 16), (x + 4, SU0 + 26), (x - 6, SU0 + 36)], "#9aa0a6", 2)
    f.polygon([(38, 220), (16, 236), (38, 252)], "#9aa0a6")                                 # exhaust out
    f.polygon([(1152, 222), (1132, 236), (1152, 250)], ORANGE)                              # extract in
    f.polygon([(16, 430), (38, 446), (16, 462)], BLUE)                                      # outdoor in
    f.polygon([(1132, 430), (1154, 446), (1132, 462)], ORANGE)                              # supply out
    f.text(16, 202, "Exhaust air", 12, "bold", MUTED); f.text(16, 412, "Outdoor air", 12, "bold", MUTED)
    f.text(1150, 284, "Extract air from the zone", 12, "bold", MUTED, anchor="end")
    f.text(1150, 492, "Supply air to the zone", 12, "bold", MUTED, anchor="end")

    def damper(x, y0, y1, tag):
        f.box(x - 7, y0, 14, y1 - y0, fill=WHITE, stroke=MUTED, radius=2, width=1.5)
        for k in range(4):
            yy = y0 + 8 + k * (y1 - y0 - 16) / 3
            f.line(x - 5, yy + 4, x + 5, yy - 4, MUTED, 1.5)
        f.lamp(x, (y0 + y1) / 2, T(tag), on=GREEN, r=5)

    def filt(x, y0, y1):
        f.box(x - 14, y0, 28, y1 - y0, fill=WHITE, stroke=MUTED, radius=2, width=1.5)
        n = 6; f.polyline([(x + (-10 if k % 2 == 0 else 10), y0 + 3 + k * (y1 - y0 - 6) / n) for k in range(n + 1)], MUTED, 1.5)

    def coil(x, y0, y1, colour, fill):
        f.box(x - 18, y0 - 6, 36, y1 - y0 + 12, fill=fill, stroke=colour, radius=2, width=2)
        for dx in (-8, 0, 8):
            f.line(x + dx, y0, x + dx, y1, colour, 2)

    def fan(x, y, run_tag):
        f.lamp(x, y, T(run_tag), on=GREEN, off="#e8eaed", r=24, stroke=INK)                  # body: green while running
        for a, b in (((0, -18), (0, 0)), ((15, 9), (0, 0)), ((-15, 9), (0, 0))):
            f.line(x + a[0], y + a[1], x + b[0], y + b[1], INK, 3)
        f.circle(x, y, 4, fill=INK, stroke=INK)

    def sensor(x, y):
        f.circle(x, y, 6, fill=WHITE, stroke=INK, width=1.5)

    def tapping(x, y):
        f.box(x - 5, y - 10, 10, 10, fill=WHITE, stroke=INK, radius=0, width=1.5)

    # rotor across both ducts
    f.box(RX0, 196, RX1 - RX0, 290, fill="#fff3e0", stroke=INK, radius=6, width=1.5)
    for y in range(206, 480, 12):
        f.line(RX0 + 3, y, RX1 - 3, y, "#f4b183", 1)
    f.lamp((RX0 + RX1) / 2, 341, T("SC3_CMD"), on=GREEN, r=9)

    # extract side, right to left (labels above the duct)
    damper(115, EX0, EX1, "FZ02"); f.text(100, 150, "FZ02", 13, "bold"); f.text(100, 168, "exhaust damper", 10, fill=MUTED)
    fan(220, 236, "PF01_FDB")
    f.text(180, 100, "PF01", 13, "bold"); num(180, 118, "speed, %", "PF01")
    lamp(260, 106, "start", "PF01_CMD", size=10)
    num(256, 136, "PDE20, Pa", "PDE20", size=13, lsize=10); num(180, 158, "flow, m3/s", "Q_EXH", digits=2, size=13, lsize=10)
    sensor(318, EX0); num(300, 150, "TE8, " + DEG, "TE8")
    tapping(440, EX0); num(430, 100, "PDE4, Pa", "PDE4"); num(430, 140, "frost limit, Pa", "PDE4_SP", size=13, lsize=10, fill=SPC)
    lamp(430, 186, "frost limit active", "FROST", on=AMBER, size=10)
    filt(560, EX0, EX1); f.text(540, 110, "FLT3", 13, "bold"); num(540, 130, "PDE2, Pa", "PDE2")
    sensor(990, EX0); num(975, 150, "TE7, " + DEG, "TE7")
    tapping(1080, EX0); f.text(1065, 104, "PE2", 13, "bold"); num(1065, 122, "Pa", "PE2")
    num(1065, 162, "setpoint in use, Pa", "PE2_SP", size=13, lsize=10, fill=SPC)

    # supply side, left to right (sensor values between the ducts, components below)
    damper(115, SU0, SU1, "FZ01"); f.text(100, 506, "FZ01", 13, "bold"); f.text(100, 524, "outdoor damper", 10, fill=MUTED)
    sensor(165, SU0); num(150, 360, "TE6, " + DEG, "TE6")
    filt(220, SU0, SU1); f.text(205, 506, "FLT1", 13, "bold"); num(205, 526, "PDE3, Pa", "PDE3")
    filt(300, SU0, SU1); f.text(285, 506, "FLT2", 13, "bold"); num(285, 526, "PDE1, Pa", "PDE1")
    f.text(RX0, 506, "SC3", 13, "bold"); num(RX0, 524, "speed, %", "SC3")
    lamp(RX0, 566, "drive ok", "SC3_OK", on=GREEN, off=RED, size=10)
    f.text(RX0 + 16, 584, "(lamp in rotor: start)", 9, fill=MUTED)
    num(RX0, 604, "efficiency, %", "HRU_EFF", size=13, lsize=10)
    sensor(480, SU0); num(465, 360, "TE3, " + DEG, "TE3")
    sensor(630, SU0); num(615, 360, "TE4, " + DEG, "TE4")
    sensor(790, SU0); num(775, 360, "TE5, " + DEG, "TE5")
    coil(550, SU0, SU1, RED, "#fdecea"); coil(710, SU0, SU1, BLUE, "#e8f0fe")
    fan(860, 446, "TF01_FDB")
    f.text(836, 506, "TF01", 13, "bold"); num(836, 524, "speed, %", "TF01"); lamp(900, 510, "start", "TF01_CMD", size=10)
    num(836, 566, "PDE10, Pa", "PDE10", size=13, lsize=10); num(836, 604, "flow, m3/s", "Q_SUP", digits=2, size=13, lsize=10)
    sensor(990, SU0); num(975, 312, "TE2, " + DEG, "TE2"); num(975, 354, "setpoint in use, " + DEG, "ACT_SP", size=13, lsize=10, fill=SPC)
    tapping(1080, SU0); num(1065, 312, "PE1, Pa", "PE1"); num(1065, 354, "setpoint in use, Pa", "PE1_SP", size=13, lsize=10, fill=SPC)

    # water side: supply pipe on the side where the air leaves the coil, return where it enters
    for xr, xs, colour, ret_label, sup_label in ((538, 562, RED, "return", "heating water in"),
                                                 (698, 722, BLUE, "return", "chilled water in")):
        f.line(xr, SU1 + 6, xr, 700, colour, 3, dash="6,4"); f.line(xs, SU1 + 6, xs, 700, colour, 4)
        f.text(xr - 4, 714, ret_label, 10, fill=MUTED, anchor="end"); f.text(xs + 4, 714, sup_label, 10, fill=MUTED)
    f.text(580, 506, "HC1", 13, "bold"); f.text(740, 506, "CC1", 13, "bold")
    sensor(538, 506); num(478, 520, "TE1, " + DEG, "TE1", size=14, lsize=10)
    lamp(478, 566, "freeze", "FREEZE", on=RED, size=10)
    f.lamp(562, 600, T("P1_FDB"), on=GREEN, r=13, stroke=INK)                               # pump P1 on the supply pipe
    f.polygon([(556, 607), (562, 593), (568, 607)], "none", INK, 1.5)
    f.text(582, 596, "P1", 13, "bold"); lamp(582, 620, "cmd", "P1_CMD", size=10)
    for xv, tag in ((538, "TV1"), (698, "TV2")):                                            # control valves on the return
        f.polygon([(xv - 9, 648), (xv + 9, 648), (xv, 660)], WHITE, INK, 1.5)
        f.polygon([(xv - 9, 672), (xv + 9, 672), (xv, 660)], WHITE, INK, 1.5)
        num(xv - 62, 652, tag + ", %", tag, size=14, lsize=10)

    # ---- bottom panels ------------------------------------------------------------------------------------------------
    def panel(x, w, title):
        f.box(x, 732, w, 158, fill=WHITE, stroke="#c4c9cf"); f.text(x + 12, 756, title, 14, "bold")
    panel(10, 370, "Zone")
    for k, tag in enumerate(("TE10_1", "TE10_2", "TE10_3")):
        num(22 + k * 88, 780, tag.replace("_", ".") + ", " + DEG, tag)
    num(22, 830, "Room mean, " + DEG, "ROOM_AVG")
    lamp(200, 828, "HS10 extended run button", "HS10", size=11)
    lamp(200, 856, "extended run active", "HS10_EXT", size=11)
    panel(390, 370, "Outdoor and safety")
    num(402, 780, "TE00 outdoor, " + DEG, "TE00"); num(540, 780, "yesterday's mean, " + DEG, "OT_DAY")
    lamp(402, 838, "SB01 emergency stop (green = normal)", "SB01", on=GREEN, off=RED)
    lamp(402, 864, "FA01 fire alarm contact (green = normal)", "FA01", on=GREEN, off=RED)
    panel(770, 390, "Setpoints in use")
    num(782, 780, "supply air, " + DEG, "ACT_SP", fill=SPC); num(912, 780, "supply duct, Pa", "PE1_SP", fill=SPC)
    num(1042, 780, "extract duct, Pa", "PE2_SP", fill=SPC); num(782, 830, "rotor frost limit, Pa", "PDE4_SP", fill=SPC)
    f.text(782, 880, "topics: " + pts[0]["topic"].rsplit("/", 2)[0] + "/<Module>/<Signal>, broker 127.0.0.1:1883", 10, fill=MUTED)

    # ---- alarms ---------------------------------------------------------------------------------------------------
    f.box(1170, 82, 360, 808, fill=WHITE, stroke="#c4c9cf"); f.text(1182, 106, "Alarms", 14, "bold")
    f.text(1182, 124, "grey normal, red alarm (class C amber), pale acknowledged,", 10, fill=MUTED)
    f.text(1182, 138, "blue reset not acknowledged, white disabled, purple fault", 10, fill=MUTED)
    lamp(1182, 164, "Critical alarm (unit stopped)", "CRIT", on=RED, size=12)
    for k, (name, cls, label) in enumerate(make_mqtt.ALARMS):
        y = 192 + k * 21
        hot, pale = (AMBER, "#fde293") if cls == "C" else (RED, "#f6aea9")
        lamp(1182, y, label, name, size=11, ranges=[(0, 0, GREY), (1, 1, hot), (2, 2, pale), (3, 3, "#8ab4f8"),
                                                     (4, 4, WHITE), (5, 5, "#a142f4")])
        f.text(1516, y, cls, 11, fill=MUTED, anchor="end")

    unused = sorted(set(t) - used)
    if unused:
        raise SystemExit(f"published but not shown: {', '.join(unused)}")
    return f, pts


if __name__ == "__main__":
    a = sys.argv[1:]
    f, pts = build(*(a[:2]))
    out = os.path.join(HERE, "AHU01.fuxa.json")
    f.save(out)
    print(f"AHU01.fuxa.json: {f.stats()}, view {W} x {H}, {os.path.getsize(out)} bytes")
