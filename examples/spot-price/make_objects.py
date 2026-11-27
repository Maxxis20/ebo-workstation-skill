#!/usr/bin/env python3
"""make_objects.py ['/Server 1'] [SpotPrice] [--area FI] [--broker 127.0.0.1] - the objects around the program,
and every binding.

  SpotPrice-values.xml  import below <server>/<folder>: folder Spot (the bridge's values, each with the bridge's id
                        as Foreign address: spot.now, spot.h0 ...) and folder Set (the operator settings, defaults)
  SpotPrice-iot.xml     import below <server>: IoT Interface <folder>_IoT with
                          client Prices  topic spot/<AREA>/points: the bridge's list [{"id": "spot.now", "v": 12.3},
                                         ...]; one client takes them all (command root = the list, point id /id =
                                         the Foreign address, value /v). THE AREA IS CHOSEN HERE, by the topic only.
                          client Test    topic spotprice/cmd: settings written by the tests ({"pointId": "<path>",
                                         "value": n}); groups Out1..3 publish the program's signals (test trace)
  binds.json            program inputs <- Spot / Set values; graphic bind names <- program signals and values

The broker is a placeholder (default 127.0.0.1: a broker on the EBO machine itself).
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from objects import ObjectSet
import xml.etree.ElementTree as ET

ap = argparse.ArgumentParser()
ap.add_argument("server", nargs="?", default="/Server 1")
ap.add_argument("folder", nargs="?", default="SpotPrice")
ap.add_argument("--area", default="FI", help="bidding zone of the bridge: FI, SE3, NO1, EE ...")
ap.add_argument("--broker", default="127.0.0.1", help="MQTT broker the bridge publishes to")
a = ap.parse_args()
base = f"{a.server}/{a.folder}"
io = json.load(open(os.path.join(HERE, "io.json")))
hmi = json.load(open(os.path.join(HERE, "hmi_binds.json")))

# the bridge's ids this example takes (CONTRACT.md, topic 'points'); the program and the graph need these
SPOT = ["valid", "beat", "hour", "quarter", "now", "now15", "now_total", "rank", "avg", "min", "max", "known",
        "known15", "tomorrow_ok", "age_s"]
SPOT += [f"h{k}" for k in range(24)] + [f"r{k}" for k in range(24)] + [f"u{k}" for k in range(48)] + [f"blk{n}" for n in range(1, 13)] + [f"q{k}" for k in range(96)]
SET = {"Ctl_On": 1, "Mode": 0, "N_Cheap": 6, "N_Block": 5, "Block_Above": 20, "Force_Below": 0, "Normal_Demand": 1,
       "Res": 0, "Unit_MWh": 0}
for i in io["inputs"]:
    f, n = i["source"].split("/")
    assert (n in SPOT) if f == "Spot" else (n in SET), i

v = ObjectSet(base)
fs = v.folder("Spot")
for n in SPOT:
    v.value(fs, n, 0, foreign=f"spot.{n}")
ft = v.folder("Set")
for n, d in SET.items():
    v.value(ft, n, d)
v.save(os.path.join(HERE, "SpotPrice-values.xml"))


def client(where, name, topic, id_ptr, v_ptr, root=None, targets=()):
    props = {"URL": a.broker, "EnableTLS": 0, "Enabled": 1, "ValueFormat": "@(Value)", "SubscriptionTopic": topic,
             "JsonPtrPointID": id_ptr, "JsonPtrValue": v_ptr, "ScaleToBaseSIUnit": 0}
    if root is not None:
        props["JsonPtrCommandRoot"] = root
    c = b.obj(where, "iot.StandardMQTT", name, props)
    g = b.mqtt_group(c, "In", list(targets), event_driven=False)
    g.find("PI[@Name='EnableInterval']").set("Value", "0")
    ET.SubElement(g, "PI", {"Name": "AllowSubscription", "Value": "1"})
    return c


OUT = [["Ctl/Reason", "Ctl/Load_Cmd", "Ctl/No_Price", "Ctl/Stale", "Ctl/Beat_Age", "Ctl/Chosen", "Ctl/Block_Mode", "Ctl/Price_Used", "Ctl/Res15"],
       ["Plan/Planned", "Plan/Plan_Wait", "Plan/Plan_Left", "Plan/In_Block", "Plan/Replan", "Plan/Hour_Tick",
        "Block/Best_In", "Block/Best_OK"],
       ["Inputs/Valid", "Inputs/Beat", "Inputs/Hour", "Inputs/Price", "Inputs/Rank", "Inputs/Known",
        "Hmi/N_Price"]]
for grp in OUT:
    for s in grp:
        assert s in io["public"] or s.startswith("Inputs/"), s
b = ObjectSet(a.server)
i = b.obj(None, "iot.IoTInterface", f"{a.folder}_IoT")
client(i, "Prices", f"spot/{a.area}/points", "/id", "/v", root="", targets=[f"{base}/Spot/{n}/Value" for n in SPOT])
t = client(i, "Test", "spotprice/cmd", "/pointId", "/value", targets=[f"{base}/Set/{n}/Value" for n in SET])
for k, grp in enumerate(OUT, 1):
    b.mqtt_group(t, f"Out{k}", [f"{base}/SPOT/{s}" for s in grp], seconds=10)
b.save(os.path.join(HERE, "SpotPrice-iot.xml"))

out = [[f"{a.folder}/SPOT/{x['module']}", x["tag"], f"{base}/{x['source']}/Value"] for x in io["inputs"]]
out += [[f"{a.folder}/Graphic", name, f"{base}/{tg}"] for name, tg in hmi.items()]
json.dump(out, open(os.path.join(HERE, "binds.json"), "w"), indent=0)
print(f"SpotPrice-values.xml (Spot {len(SPOT)}, Set {len(SET)}), SpotPrice-iot.xml (area {a.area}, broker "
      f"{a.broker}), binds.json ({len(out)} bindings)")
