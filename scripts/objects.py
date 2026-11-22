#!/usr/bin/env python3
"""objects.py - write an EBO import file (.xml) with objects that need no editor: folders, trend logs, alarms,
values, trend charts. Load it with the driver: Ws-Import '/Server 1' 'C:\\agentwork\\ebo\\X.xml' (about 7 s).

    from objects import ObjectSet
    s = ObjectSet(parent="/Server 1")                 # where the file will be imported
    f = s.folder("DH-ex2-Logs")
    log = s.trend_log(f, "TE1", "/Server 1/DH-ex2/TC1_DHW/TE1", seconds=60)
    s.trend_chart(f, "Temperatures", [log])
    s.alarm_range(f, "TE1_HIGH", "/Server 1/DH-ex2/TC1_DHW/TE1", high=65, low=40, text="DHW temperature")
    s.save("logs.xml")

A target is an absolute path ending in the property: '/Server 1/Program/MODULE/Signal'. It is stored relative to
the object that reads it, which is what WorkStation writes itself. Property names were taken from production
exports and each object type here was imported on EBO 7.1 (reference/findings.md, "Objects from a file").
An object whose name is already there is imported beside it as Name_2: delete the old one first.
"""
import posixpath
import xml.etree.ElementTree as ET


class ObjectSet:
    def __init__(self, parent="/Server 1", version="7.1.1.132"):
        self.parent, self.version = parent.rstrip("/"), version
        self.top = ET.Element("ExportedObjects")
        self.path = {id(self.top): self.parent}

    # --- generic -----------------------------------------------------------------------------------------------
    def obj(self, where, typ, name, values=None, refs=None, descr="", hidden=False):
        """Any object of a built-in type. values: {property: value}; refs: {property: absolute target}, where a
        target without a property part is written as '/path/to/object/' (trailing slash)."""
        e = ET.SubElement(self.top if where is None else where, "OI", {"NAME": name, "TYPE": typ})
        if descr:
            e.set("DESCR", descr)
        if hidden:
            e.set("hidden", "1")
        me = self.path[id(self.top if where is None else where)] + "/" + name
        self.path[id(e)] = me
        for k, v in (values or {}).items():
            ET.SubElement(e, "PI", {"Name": k, "Value": _fmt(v)})
        for k, target in (refs or {}).items():
            t_obj, t_prop = target.rsplit("/", 1)
            r = ET.SubElement(ET.SubElement(e, "PI", {"Name": k}), "Reference",
                              {"DeltaFilter": "0", "Object": posixpath.relpath(t_obj, me), "Retransmit": "0",
                               "TransferRate": "10"})
            if t_prop:
                r.set("Property", t_prop)
        return e

    def where(self, e):
        """Absolute path an object will have after the import (to use as a target)."""
        return self.path[id(e)]

    # --- the usual ones ----------------------------------------------------------------------------------------
    def folder(self, name, where=None):
        return self.obj(where, "system.base.Folder", name)

    def value(self, where, name, value=0, kind="AV", source=None):
        """Server value: AV analog, BV binary, SV string. source: a target the value follows."""
        return self.obj(where, "server.point." + kind, name, None if source else {"Value": value},
                        {"Value": source} if source else None)

    def trend_log(self, where, name, target, seconds=60, size=20000):
        """Interval trend log of one signal."""
        return self.obj(where, "trend.TLog", name, {"Interval": int(seconds * 1000), "LogSize": size, "Enabled": 1},
                        {"LogPoint": target})

    def trend_log_cov(self, where, name, target, delta=0.5, size=20000):
        """Change-of-value trend log: a record whenever the signal has moved by delta."""
        return self.obj(where, "trend.TLogChangeOfValue", name, {"DeltaValue": delta, "LogSize": size, "Enabled": 1},
                        {"LogPoint": target})

    def trend_chart(self, where, name, logs, title=""):
        """Trend chart showing trend logs made in this set (the objects returned by trend_log)."""
        c = self.obj(where, "trend.view.GraphicalTrendView", name, {"NOTE1": title} if title else None)
        for log in logs:
            self.obj(c, "trend.view.TrendLogSeriesProperties", log.get("NAME") + " Series", None,
                     {"DisplayLog": self.where(log) + "/"}, hidden=True)
        return c

    def alarm_state(self, where, name, target, text="", reset_text="", priority=100, delay=0, descr=""):
        """Alarm while a binary signal is true."""
        return self.obj(where, "alarm.ChangeOfStateAlarm", name,
                        {"AlarmMessage": text or name, "ResetMessage": reset_text or (text or name),
                         "AlarmPriority": priority, "ResetPriority": priority, "TimeDelayToOffNormal": delay},
                        {"MonitoredVariable": target}, descr)

    def alarm_range(self, where, name, target, high, low, text="", reset_text="", priority=100, delay=0, descr=""):
        """Alarm when an analog signal is above high or below low."""
        return self.obj(where, "alarm.OutOfRangeAlarm", name,
                        {"HighLimit": high, "LowLimit": low, "HighLimitMessage": text or name,
                         "LowLimitMessage": text or name, "ResetMessage": reset_text or (text or name),
                         "HighLimitPriority": priority, "LowLimitPriority": priority, "ResetPriority": priority,
                         "TimeDelayToOffNormal": delay}, {"MonitoredVariable": target}, descr)

    def alarm_deviation(self, where, name, target, setpoint, above, below, text="", priority=100, delay=0, descr=""):
        """Alarm when a signal is more than `above` over or `below` under a setpoint signal."""
        return self.obj(where, "alarm.OutOfReferenceRangeAlarm", name,
                        {"HighDiffLimit": above, "LowDiffLimit": below, "HighLimitMessage": text or name,
                         "LowLimitMessage": text or name, "ResetMessage": text or name, "HighLimitPriority": priority,
                         "LowLimitPriority": priority, "TimeDelayToOffNormal": delay},
                        {"MonitoredVariable": target, "SetpointReference": setpoint}, descr)

    # --- output ------------------------------------------------------------------------------------------------
    def save(self, path):
        root = ET.Element("ObjectSet", {"ExportMode": "Special", "Note": "TypesFirst", "Version": self.version})
        m = ET.SubElement(root, "MetaInformation")
        for k, v in (("ExportMode", "Special"), ("RuntimeVersion", self.version), ("SourceVersion", self.version),
                     ("ServerFullPath", "/" + self.parent.strip("/").split("/")[0])):
            ET.SubElement(m, k, {"Value": v})
        root.append(self.top)
        ET.indent(root)
        ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)
        return path


def _fmt(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


if __name__ == "__main__":
    import sys
    s = ObjectSet(); f = s.folder("Demo")
    log = s.trend_log(f, "TE1", "/Server 1/DH-ex2/TC1_DHW/TE1", seconds=10)
    s.trend_chart(f, "Chart", [log], "Temperature")
    s.alarm_range(f, "TE1_HIGH", "/Server 1/DH-ex2/TC1_DHW/TE1", 65, 40, "DHW temperature")
    s.save(sys.argv[1] if len(sys.argv) > 1 else "demo.xml")
