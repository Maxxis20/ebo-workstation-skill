#!/usr/bin/env python3
"""Shared point lists of the DH-ex2 example: program bindings, graphic bindings, MQTT data points.

    python3 points.py bind-prog | bind-hmi | mqtt      prints the PowerShell for ebo.sh run
"""
import sys
C, S = "DH-ex2", "DH-ex2-SIM"

# program input -> public signal of the other program (both directions)
PROG_BINDS = {
    C: [("TE2B_IN", S, "PLANT", "TE2B"), ("TE1_IN", S, "PLANT", "TE1"), ("TE2A_IN", S, "PLANT", "TE2A")],
    S: [("TV1_IN", C, "TC1_DHW", "TV1"), ("P1_IN", C, "TC1_DHW", "P1_RUN"),
        ("TV2_IN", C, "TC2_HEAT", "TV2"), ("P2_IN", C, "TC2_HEAT", "P2_RUN")],
}

# graphic bind name -> (program, module, signal)
HMI = {
    "TOUT": (S, "PLANT", "TOUT"), "DHW_TAP": (S, "PLANT", "DHW_TAP"),
    "TV1_POS": (S, "PLANT", "TV1_POS"), "TV2_POS": (S, "PLANT", "TV2_POS"),
    "TE2B": (C, "OUTDOOR", "TE2B"), "TE2B_F": (C, "OUTDOOR", "TE2B_F"),
    "TE1": (C, "TC1_DHW", "TE1"), "DHW_SP": (C, "TC1_DHW", "DHW_SP"), "TV1": (C, "TC1_DHW", "TV1"),
    "P1_RUN": (C, "TC1_DHW", "P1_RUN"),
    "TE2A": (C, "TC2_HEAT", "TE2A"), "HEAT_SP": (C, "TC2_HEAT", "HEAT_SP"), "TV2": (C, "TC2_HEAT", "TV2"),
    "P2_RUN": (C, "TC2_HEAT", "P2_RUN"), "SUMMER": (C, "TC2_HEAT", "SUMMER"),
    "TE2B_FAULT": (C, "OUTDOOR", "TE2B_FAULT"), "TE1_FAULT": (C, "TC1_DHW", "TE1_FAULT"),
    "DHW_TEMP_ALM": (C, "TC1_DHW", "DHW_TEMP_ALM"), "TE2A_FAULT": (C, "TC2_HEAT", "TE2A_FAULT"),
    "HEAT_TEMP_ALM": (C, "TC2_HEAT", "HEAT_TEMP_ALM"), "ALARM_SUM": (C, "ALARM", "ALARM_SUM"),
}

# MQTT data points: tag name -> (program, module, signal); topic = "Server 1/<program>/<module>/<signal>"
MQTT = {
    "TOUT": (S, "PLANT", "TOUT"), "TE2B": (C, "OUTDOOR", "TE2B"), "TE2B_F": (C, "OUTDOOR", "TE2B_F"),
    "TE1": (C, "TC1_DHW", "TE1"), "DHW_SP": (C, "TC1_DHW", "DHW_SP"), "TV1": (C, "TC1_DHW", "TV1"),
    "P1_RUN": (C, "TC1_DHW", "P1_RUN"),
    "TE2A": (C, "TC2_HEAT", "TE2A"), "HEAT_SP": (C, "TC2_HEAT", "HEAT_SP"), "TV2": (C, "TC2_HEAT", "TV2"),
    "P2_RUN": (C, "TC2_HEAT", "P2_RUN"), "ALARM_SUM": (C, "ALARM", "ALARM_SUM"),
    "TV1_POS": (S, "PLANT", "TV1_POS"), "P1_ON": (S, "PLANT", "P1_ON"),
    "TV2_POS": (S, "PLANT", "TV2_POS"), "P2_ON": (S, "PLANT", "P2_ON"),
}


def path(t):
    return "/Server 1/" + "/".join(t)


def topic(t):
    return "Server 1/" + "/".join(t)


def bind_cmd(obj, pairs):
    return "Log (Ws-Bind '/Server 1/%s' @(%s))" % (obj, ",".join("@('%s','%s')" % (n, p) for n, p in pairs))


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "bind-prog":
        print("; ".join(bind_cmd(o, [(n, path(t)) for n, *t in rows]) for o, rows in PROG_BINDS.items()))
    elif what == "bind-hmi":
        print(bind_cmd("DH-ex2-HMI", [(n, path(t)) for n, t in HMI.items()]))
    elif what == "mqtt":
        pts = ",".join("@(@('%s','%s'),'%s')" % t for t in MQTT.values())
        print("if (-not (Ws-TreeItem '/Server 1/IoT')) { Log (Ws-New '/Server 1' 'IoT Interface' 'IoT') }; "
              "Log (Mq-Client '/Server 1/IoT' 'Broker'); Log (Mq-Group '/Server 1/IoT/Broker' 'DH' @(%s))" % pts)
    elif what == "topics":
        print("\n".join(topic(t) for t in MQTT.values()))
