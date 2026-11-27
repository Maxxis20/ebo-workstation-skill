#!/usr/bin/env python3
"""make_objects.py ['/Server 1'] [FanSeq] - the objects around the program, and every binding.

  FanSeq-cmd.xml   import below <server>/<folder>: folder Cmd with the server values the program reads (Mode,
                   Auto_Demand, E_Stop, Reset, Fault_Damper, Fault_Fan). The graphic writes them; so can MQTT.
  FanSeq-iot.xml   import below <server>: IoT Interface <folder>_IoT with MQTT client Mqtt (broker 127.0.0.1):
                   group In takes commands (topic fanseq/cmd, {"pointId": "<server>/<folder>/Cmd/<name>/Value",
                   "value": n}); groups Out1, Out2 publish the sequence signals under their EBO path (the test trace).
  binds.json       program inputs <- Cmd values; graphic bind names <- program signals and Cmd values
                   (for `ebox.py bind` on a Special export of the folder).
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from objects import ObjectSet
import xml.etree.ElementTree as ET

args = [a for a in sys.argv[1:] if not a.startswith("--")]
server = args[0] if args else "/Server 1"; folder = args[1] if len(args) > 1 else "FanSeq"
base = f"{server}/{folder}"
io = json.load(open(os.path.join(HERE, "io.json")))
hmi = json.load(open(os.path.join(HERE, "hmi_binds.json")))
CMD = [i["tag"] for i in io["inputs"]]

v = ObjectSet(base)
f = v.folder("Cmd")
for n in CMD:
    v.value(f, n, 0)
v.save(os.path.join(HERE, "FanSeq-cmd.xml"))

OUT1 = ["Seq/Step", "Seq/Step_Time", "Seq/RQ_AT", "Seq/FBAD", "Seq/Sup_Time", "Seq/Seq_Alarm", "Seq/AL_Step",
        "Seq/AL_Req", "Seq/Trip", "Seq/Demand"]
OUT2 = ["Seq/D1", "Seq/D2", "Seq/D3", "Seq/D4", "Seq/D5", "Outputs/Damper_Cmd", "Outputs/Fan_Cmd", "Sim/Damper_Pos",
        "Sim/Fan_Fdb", "Sim/Duct_Pressure"]
for s in OUT1 + OUT2:
    assert s in io["public"], s
b = ObjectSet(server)
i = b.obj(None, "iot.IoTInterface", f"{folder}_IoT")
c = b.obj(i, "iot.StandardMQTT", "Mqtt", {
    "URL": "127.0.0.1", "EnableTLS": 0, "Enabled": 1, "ValueFormat": "@(Value)",
    "SubscriptionTopic": "fanseq/cmd", "JsonPtrPointID": "/pointId", "JsonPtrValue": "/value",
    "ScaleToBaseSIUnit": 0})
gi = b.mqtt_group(c, "In", [f"{base}/Cmd/{n}/Value" for n in CMD], event_driven=False)
gi.find("PI[@Name='EnableInterval']").set("Value", "0")
ET.SubElement(gi, "PI", {"Name": "AllowSubscription", "Value": "1"})
for name, pts in (("Out1", OUT1), ("Out2", OUT2)):
    b.mqtt_group(c, name, [f"{base}/SEQ/{s}" for s in pts], seconds=10)
b.save(os.path.join(HERE, "FanSeq-iot.xml"))

out = [[f"{folder}/SEQ/Inputs", n, f"{base}/Cmd/{n}/Value"] for n in CMD]
out += [[f"{folder}/Graphic", name, f"{base}/{t}"] for name, t in hmi.items()]
json.dump(out, open(os.path.join(HERE, "binds.json"), "w"), indent=0)
print(f"FanSeq-cmd.xml ({len(CMD)} values), FanSeq-iot.xml (In {len(CMD)}, Out1 {len(OUT1)}, Out2 {len(OUT2)}), "
      f"binds.json ({len(out)} bindings)")
