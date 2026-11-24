#!/usr/bin/env python3
"""objects.py - write an EBO import file (.xml) with objects that need no editor: folders, trend logs, alarms,
values, weekly schedules, trend charts, dashboards with their widgets. Load it with the driver: Ws-Import '/Server 1' 'C:\\agentwork\\ebo\\X.xml' (about 7 s).

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

    def value(self, where, name, value=0, kind="AV", source=None, unit=None, foreign=None):
        """Server value: AV analog, BV binary, SV string. source: a target the value follows. unit: a text of
        UNIT or an EBO unit code ('0x280001'). foreign: Foreign address (a point id for MQTT subscription)."""
        e = self.obj(where, "server.point." + kind, name, None if source else {"Value": value},
                     {"Value": source} if source else None)
        if unit:
            e.find("PI[@Name='Value']").set("Unit", self.UNIT.get(unit, unit))
        if foreign:
            ET.SubElement(e, "PI", {"Name": "ForeignAddress", "Value": foreign})
        return e

    # unit code = prefix (0xfd milli, 0x03 kilo) << 24 | category id << 16 | unit id (definitions/system/units)
    UNIT = {"\xb0C": "0x280001", "%": "0x200001", "%RH": "0x170001", "ppm": "0x200002", "Pa": "0x230002",
            "s": "0x2e0007", "V": "0x320001", "mV": "0xfd320001"}

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

    DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

    def schedule(self, where, name, week, descr=""):
        """Digital weekly schedule (on / off). week: {day: [("06:30", "18:30"), ...]} with day 1 = Monday ... 7 =
        Sunday, or the strings "mon-fri", "sat-sun", "all". Bind a program input to its Value."""
        days = {}
        for k, spans in week.items():
            for d in {"mon-fri": range(1, 6), "sat-sun": (6, 7), "all": range(1, 8)}.get(k, (k,)):
                days.setdefault(d, []).extend(spans)
        sc = self.obj(where, "schedule.NSPDigitalSchedule", name, descr=descr)
        T = "system.schedulecommon.propertytypes."
        for d in range(1, 8):
            ws = ET.SubElement(sc, "OI", {"NAME": f"WS{d:05d}", "TYPE": T + "DailySchedule", "DESCR": self.DAYS[d - 1],
                                          "declared": "1", "hidden": "1"})
            ET.SubElement(ws, "PI", {"Name": "DayOfWeek", "Value": str(d)})
            n = 0
            for a, b in sorted(days.get(d, [])):
                for t, on in ((a, True), (b, False)):
                    n += 1; hh, mm = (int(v) for v in t.split(":"))
                    tv = ET.SubElement(ws, "OI", {"NAME": f"TVP{n:05d}", "TYPE": T + "tvp.OnOffTimeValuePair", "hidden": "1"})
                    ET.SubElement(tv, "PI", {"Name": "Hour", "Value": str(hh)})
                    if mm:
                        ET.SubElement(tv, "PI", {"Name": "Minute", "Value": str(mm)})
                    ET.SubElement(tv, "PI", {"Name": "Value", "Value": "1"} if on else {"Name": "Value", "Null": "1"})
        self.path[id(sc)] = self.path[id(self.top if where is None else where)] + "/" + name
        return sc

    def mqtt_group(self, where, name, targets, seconds=10, event_driven=True):
        """Data group of an MQTT client (iot.DataGroup): the points it publishes. targets: absolute paths
        '/Server 1/Program/MODULE/Signal'. Import below the MQTT client: ObjectSet(parent='/Server 1/IoT/Broker'),
        where=None. Each point goes out under the topic of its own path, on change and every `seconds`."""
        e = self.obj(where, "iot.DataGroup", name)
        me = self.path[id(e)]
        dp = ET.SubElement(e, "PI", {"Name": "DataPoints"})
        for t in targets:
            t_obj, t_prop = t.rsplit("/", 1)
            ET.SubElement(dp, "Reference", {"DeltaFilter": "0", "Object": posixpath.relpath(t_obj, me),
                                            "Property": t_prop, "Retransmit": "0", "TransferRate": str(seconds)})
        for k, v in (("EnableInterval", 1), ("EventDriven", int(event_driven)), ("Interval", seconds)):
            ET.SubElement(e, "PI", {"Name": k, "Value": str(v)})
        return e

    def mqtt_subscriber(self, where, name, host, topic, target, value_ptr, id_ptr="/pointId", group="In"):
        """MQTT client (iot.StandardMQTT) that takes one value from the broker, with its one Data Group: Allow
        subscription on, interval and event publishing off, so it sends nothing. where: an IoT Interface element of
        this set (iot.IoTInterface, at most 4 clients each), or None with ObjectSet(parent='/Server 1/IoT').
        target: absolute path '/Server 1/Folder/name/Value'. A message on `topic` is written to the target when the
        JSON pointer id_ptr gives its point id (its foreign address, its full path or its nspg id) and value_ptr its
        value; both pointers hold for the whole client, so one client per value (findings, "MQTT subscription")."""
        c = self.obj(where, "iot.StandardMQTT", name, {
            "URL": host, "EnableTLS": 0, "Enabled": 1, "ValueFormat": "@(Value)",
            "SubscriptionTopic": topic, "JsonPtrPointID": id_ptr, "JsonPtrValue": value_ptr,
            "ScaleToBaseSIUnit": 0})
        g = self.mqtt_group(c, group, [target], event_driven=False)
        g.find("PI[@Name='EnableInterval']").set("Value", "0")
        ET.SubElement(g, "PI", {"Name": "AllowSubscription", "Value": "1"})
        return c

    # --- dashboards (shown in WebStation; WorkStation only lists their settings) -------------------------------
    W = "client.dashboard.widgets."
    ICON = {"none": 0, "co2": 1, "cooling": 2, "electricity": 3, "heating": 4, "temperature": 5, "water": 6,
            "lights": 7, "blinds": 8}
    PERIOD = {"today": 0, "this week": 1, "this month": 2, "this year": 3, "last hour": 17, "last 24 hours": 7,
              "last 7 days": 8, "last 30 days": 9, "last 12 months": 10}
    CHART = {"bar": 0, "area": 1, "curve": 2, "line": 3}
    CALC = {"max": 1, "min": 2, "average": 3, "sum": 4, "delta": 5, "meter": 6}

    def gauge(self, where, name, target, lo=0, hi=100, guides=(), title="", needle=False):
        """Round gauge of a live signal. guides: (value, '#RRGGBB') marks on the scale."""
        g = self.obj(where, self.W + "PointGaugeWidget", name,
                     {"Min": lo, "Max": hi, "UseNeedle": needle, **({"DESCR": title} if title else {})},
                     {"DisplaySignal": target})
        for i, (v, col) in enumerate(guides, 1):
            self.obj(g, self.W + "GuideProperties", f"Guide{i}", {"Value": v, "Color": _colour(col)}, hidden=True)
        return g

    def point_values(self, where, name, points, title=""):
        """Big live numbers. points: (label, target, icon name from ICON)."""
        w = self.obj(where, self.W + "PointValueWidget", name, {"DESCR": title} if title else None)
        for label, target, icon in points:
            self.obj(w, self.W + "PointGuideSeriesProperties", label, {"WidgetIcon": self.ICON[icon]},
                     {"DisplaySignal": target}, hidden=True)
        return w

    def period_chart(self, where, name, logs, period="last 24 hours", kind="line", calc="average", title=""):
        """Chart of trend logs made in this set over a period (PERIOD), drawn as CHART, each bucket by CALC."""
        w = self.obj(where, self.W + "PeriodChartWidget", name,
                     {"Period": self.PERIOD[period], **({"DESCR": title} if title else {})})
        for log in logs:
            self.obj(w, self.W + "ChartSeriesProperties", log.get("NAME") + " Series",
                     {"ChartType": self.CHART[kind], "CalculationMethod": self.CALC[calc]},
                     {"DisplayLog": self.where(log) + "/"}, hidden=True)
        return w

    def log_gauge(self, where, name, log, lo=0, hi=100, period="last 24 hours", calc="average", title=""):
        """Gauge of a trend log's average / max / sum over a period."""
        return self.obj(where, self.W + "LogGaugeWidget", name,
                        {"Min": lo, "Max": hi, "Period": self.PERIOD[period], "CalculationMethod": self.CALC[calc],
                         **({"DESCR": title} if title else {})}, {"DisplayLog": self.where(log) + "/"})

    def alarm_count(self, where, name, title=""):
        """Number of active alarms with a small history curve."""
        return self.obj(where, self.W + "AlarmCountWidget", name, {"DESCR": title} if title else None)

    def dashboard(self, where, name, tiles, show_time=True):
        """Dashboard page. tiles: (widget object from this set, or absolute path of any object that can be shown:
        a graphic, a trend chart; columns, rows), placed in the order given."""
        d = self.obj(where, "client.dashboard.Dashboard", name, {"ShowTime": show_time})
        for i, (w, cols, rows) in enumerate(tiles):
            path = w if isinstance(w, str) else self.where(w)
            self.obj(d, "client.dashboard.DashboardWidget", path.rsplit("/", 1)[-1],
                     {"ColumnSpan": cols, "RowSpan": rows, "Order": i}, {"InitialAddress": path + "/"}, hidden=True)
        return d

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


def _colour(c):
    """'#RRGGBB' -> EBO colour number (signed 32 bit ARGB, opaque)."""
    if isinstance(c, int):
        return c
    v = 0xFF000000 | int(c.lstrip("#"), 16)
    return v - (1 << 32) if v >= (1 << 31) else v


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
