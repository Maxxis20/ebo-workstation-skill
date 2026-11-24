#!/usr/bin/env python3
"""make.py: EBO objects that take the values of a LoRaWAN sensor from an MQTT broker fed by a LoRaWAN network
server that publishes in ChirpStack (v4) format.

    python3 make.py --deveui <16 hex> [--host 127.0.0.1] [--name Sensor01] [--iot LoRa] [--topic T]
                    [--signals name=/json/pointer[@unit],...] [--server '/Server 1']
        -> lora_values.xml   import below /Server 1   (folder <name> with one analog value per signal)
           lora_iot.xml      import below /Server 1   (IoT Interface <iot>, <iot>_2 ... with one MQTT client per signal)

The network server publishes one JSON message per uplink on application/<app>/device/<devEui>/event/up, with
all decoded values under "object" and no point id. An EBO MQTT client maps a subscribed message with two JSON
pointers that hold for the whole client: one to a point id, one to the value. So:

  - the point id pointer is /deviceInfo/devEui, and every target value carries the devEui as its Foreign address
    (EBO accepts a point's foreign address, its full path or its nspg id as the point id);
  - the value pointer differs per signal, so each signal has an MQTT client of its own. An IoT Interface holds at
    most 4 clients: the fifth signal starts interface <iot>_2, the ninth <iot>_3;
  - each client has one Data Group with Allow subscription = Yes holding the one target value. The group's
    interval publication is off and it is not event driven, so nothing is sent towards the broker.

Default signals: the decoded values of a room sensor, the radio level of the first gateway and the uplink counter.
The counter changes with every uplink, also when no reading does, so it is the one to watch for "sensor still
reporting" (make_age.py of the room-sensor example, input V1 bound to fcnt).

--name and --iot must differ: an IoT Interface and a folder of the same name break the references (README).
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from objects import ObjectSet

SIGNALS = "temperature=/object/temperature@\xb0C,humidity=/object/humidity@%RH,vdd=/object/vdd@mV,rssi=/rxInfo/0/rssi,fcnt=/fCnt"
PER_INTERFACE = 4

p = argparse.ArgumentParser()
p.add_argument("--host", default="127.0.0.1", help="MQTT broker the network server publishes to")
p.add_argument("--deveui", required=True, help="device EUI as the network server writes it (lower case hex)")
p.add_argument("--name", default="Sensor01", help="folder for the values")
p.add_argument("--iot", default="LoRa", help="IoT Interface; must differ from --name")
p.add_argument("--topic", default=None, help="subscription topic; default the sensor's uplink topic")
p.add_argument("--signals", default=SIGNALS, help="name=/json/pointer[@unit], comma separated")
p.add_argument("--server", default="/Server 1")
a = p.parse_args()
if a.name == a.iot:
    p.error("--name and --iot must differ")
topic = a.topic or f"application/default/device/{a.deveui}/event/up"
signals = []
for s in a.signals.split(","):
    n, rest = s.split("=", 1)
    ptr, _, unit = rest.partition("@")
    signals.append((n.strip(), ptr.strip(), unit.strip() or None))

v = ObjectSet(a.server)
f = v.folder(a.name)
for n, ptr, unit in signals:
    v.value(f, n, 0, unit=unit, foreign=a.deveui)
v.save(os.path.join(HERE, "lora_values.xml"))

b = ObjectSet(a.server)
names = []
for k, (n, ptr, unit) in enumerate(signals):
    if k % PER_INTERFACE == 0:
        names.append(a.iot if not k else f"{a.iot}_{k // PER_INTERFACE + 1}")
        i = b.obj(None, "iot.IoTInterface", names[-1])
    b.mqtt_subscriber(i, n, a.host, topic, f"{a.server}/{a.name}/{n}/Value", ptr, "/deviceInfo/devEui")
b.save(os.path.join(HERE, "lora_iot.xml"))
print("lora_values.xml, lora_iot.xml:", ", ".join(names), "->", a.host, topic, f"({len(signals)} signals)")
