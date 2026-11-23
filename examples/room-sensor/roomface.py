"""roomface.py - one drawing of a room sensor faceplate, used as a page of its own and as a click-open box.

face(p, ox, oy, title, temp, ...) draws into the Graphic p with its top left corner at (ox, oy). Every argument
after temp is optional: a row appears only when its bind name is given. The thermometer is blue at t_cold and
below, red at t_hot and above, and blends through green in between. age / stale: minutes since the last new
value and its too-old flag (make_age.py makes the program that gives them). Size: W x height(...).
"""
W = 250
INK = "#1F2329"; GREY = "#5F6368"; EDGE = "#C9CED6"; HEAD = "#263238"
DEG = "\xb0C"


def height(rh=None, vdd=None, mean=None, bad=None, alarm=None, note=None, age=None, stale=None):
    rows = sum(1 for r in (rh, vdd, mean, bad, age) if r) + (1 if note else 0)
    return 96 + 24 * rows + 8


def face(p, ox, oy, title, temp, rh=None, vdd=None, vdd_low=3300, mean=None, bad=None, alarm=None, note=None,
         subtitle="Room sensor", t_cold=20.0, t_hot=25.0, age=None, stale=None):
    h = height(rh, vdd, mean, bad, alarm, note, age, stale)
    p.rect(ox, oy, W, 30, fill=HEAD, stroke="None", radius=6)
    p.rect(ox, oy + 20, W, 10, fill=HEAD, stroke="None")
    p.text(ox + 10, oy + 7, title, size=13, bold=True, colour="#FFFFFF")
    p.text(ox + W - 10, oy + 9, subtitle, size=10, colour="#B0BEC5", align="Right")
    # temperature, large, with a small thermometer
    p.thermometer(ox + 11, oy + 40, temp, lo=t_cold, hi=t_hot, h=36)
    p.value(ox + 38, oy + 42, temp, decimals=1, unit=DEG, size=30, colour=INK)
    if alarm:
        p.alarm_state(ox + W - 28, oy + 48, alarm, d=16)
    y = oy + 96
    p.line(ox + 10, y - 6, ox + W - 10, y - 6, EDGE, 1)
    if rh:
        p.text(ox + 12, y + 2, "Humidity", size=12, colour=GREY)
        p.value(ox + 92, y, rh, decimals=0, unit="%", size=14, colour=INK)
        p.bar(ox + 150, y + 5, rh, w=88, h=9, full=100.0, colour="#1A73E8"); y += 24
    if vdd:
        p.text(ox + 12, y + 2, "Battery", size=12, colour=GREY)
        p.value(ox + 92, y, vdd, decimals=0, unit="mV", size=14, colour=INK)
        p.level_lamp(ox + 164, y + 2, vdd, vdd_low)
        p.text(ox + 183, y + 3, f"low {vdd_low}", size=10, colour=GREY); y += 24
    if mean:
        p.text(ox + 12, y + 2, "Room mean", size=12, colour=GREY)
        p.value(ox + 92, y, mean, decimals=1, unit=DEG, size=14, colour=INK); y += 24
    if bad:
        p.text(ox + 12, y + 2, "Sensor", size=12, colour=GREY)
        p.state(ox + 92, y + 1, bad, "FAULT", "ok", size=13, on="#D93025", off="#1E8E3E"); y += 24
    if age:
        p.text(ox + 12, y + 2, "Last new value", size=12, colour=GREY)
        p.value(ox + 108, y, age, decimals=0, unit="min ago", size=14, colour=INK)
        if stale:
            p.lamp(ox + W - 26, y + 2, stale, d=14, on="#D93025", off="#1E8E3E")
        y += 24
    if note:
        p.text(ox + 12, y + 3, note, size=10, colour=GREY)
    return h
