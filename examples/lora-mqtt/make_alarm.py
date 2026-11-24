#!/usr/bin/env python3
"""make_alarm.py: an alarm for "the sensor stopped reporting", on the Stale output of the age program.

    python3 make_alarm.py [--name Sensor01] [--program '<server>/<name>_Age'] [--server '/Server 1'] [--minutes 30]
        -> lora_alarm.xml   import below <server>/<name> (the folder of values made by make.py)

The age program is SensorAge.aut of the room-sensor example (../room-sensor/make_age.py), loaded as <name>_Age
with V1 bound to <name>/fcnt/Value: the uplink counter changes with every uplink, so Stale means no uplink for
STALE_MIN minutes. --minutes only goes into the alarm text; the limit itself is STALE_MIN in make_age.py.
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from objects import ObjectSet

p = argparse.ArgumentParser()
p.add_argument("--name", default="Sensor01", help="folder of the values (make.py --name)")
p.add_argument("--program", default=None, help="age program; default <server>/<name>_Age")
p.add_argument("--server", default="/Server 1")
p.add_argument("--minutes", type=int, default=30, help="for the alarm text only")
a = p.parse_args()
program = a.program or f"{a.server}/{a.name}_Age"

s = ObjectSet(parent=f"{a.server}/{a.name}")
s.alarm_state(None, "Stale_Alarm", f"{program}/Stale",
              text=f"{a.name}: no uplink for more than {a.minutes} min",
              reset_text=f"{a.name}: reporting again")
s.save(os.path.join(HERE, "lora_alarm.xml"))
print("lora_alarm.xml: Stale_Alarm on", f"{program}/Stale", "-> import below", f"{a.server}/{a.name}")
