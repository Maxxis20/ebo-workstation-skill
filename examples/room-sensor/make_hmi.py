#!/usr/bin/env python3
"""make_hmi.py - a room sensor as a page of its own: RoomSensor.tgml and binds.json.

The faceplate is roomface.face(); the same drawing opens as a box at the room sensors of the AHU01 example.
Bind names: T (temperature), RH (humidity), VDD (battery, mV), AGE and STALE (from the program of make_age.py).
    python3 make_hmi.py "Room 101" "/Server 1/BACnet/IP Network/Sensor/Application" Temp_Object Rh_Object Vdd_Object \\
        "/Server 1/Room101_Age"
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import tgml, roomface

title = sys.argv[1] if len(sys.argv) > 1 else "Room sensor"
base = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else "/Server 1/Sensor/Application"
names = sys.argv[3:6] if len(sys.argv) > 5 else ["temperature", "humidity", "vdd"]
age = sys.argv[6].rstrip("/") if len(sys.argv) > 6 else "/Server 1/SensorAge"     # the program from make_age.py

kw = dict(rh="RH", vdd="VDD", age="AGE", stale="STALE")
FW = roomface.W; FH = roomface.height(**kw)
g = tgml.Graphic(FW + 60, FH + 60, background="#EEF0F3")
g.rect(30, 30, FW, FH, fill="#FFFFFF", stroke="#5F6368", sw=1.5, radius=6)
roomface.face(g, 30, 30, title, "T", **kw)
g.info(FW + 36, 6, "About this sensor",
       "Values are read from the sensor's BACnet objects by the server. Thermometer: blue at 20 \xb0C and below, red "
       "at 25 \xb0C and above. Battery lamp: red at or below the low limit. Last new value: minutes since any of the "
       "three values changed; its lamp turns red after 30 minutes without a change.", w=240, side="left")
g.save(os.path.join(HERE, "RoomSensor.tgml"))
binds = [["T", f"{base}/{names[0]}/Value"], ["RH", f"{base}/{names[1]}/Value"], ["VDD", f"{base}/{names[2]}/Value"],
         ["AGE", f"{age}/Age_Min"], ["STALE", f"{age}/Stale"]]
age_inputs = [[f"V{i + 1}", f"{base}/{names[i]}/Value"] for i in range(3)]
assert sorted(g.binds) == sorted(b[0] for b in binds), g.binds
json.dump({"graphic": binds, "age_program": age_inputs}, open(os.path.join(HERE, "binds.json"), "w"), indent=1)
print(f"RoomSensor.tgml: {g.w} x {g.h}, binds {g.binds}")
