#!/usr/bin/env bash
# deploy_fuxa.sh [server path] [folder]  - publish the AHU01 signals over MQTT and load the FUXA view of the unit.
# Run after deploy.sh (it needs the program /<server>/<folder>/AHU), and again after every deploy.sh: that one
# deletes and re-imports the folder, which the data points of the groups point into.
# Makes, if missing, /<server>/IoT (IoT Interface) and its MQTT client Broker (127.0.0.1, no TLS, @(Value)),
# deletes the Data Groups AHU01_Meas, AHU01_Ctrl, AHU01_Alarms and imports them again (92 points, make_mqtt.py),
# checks on the broker that every topic arrives, then loads AHU01.fuxa.json into FUXA (http://127.0.0.1:1881/).
# Needs Mosquitto and FUXA on the EBO machine (findings, section MQTT). About 2 minutes.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); S=$H/../../scripts; E=$S/ebo.sh
SRV=${1:-/Server 1}; F=${2:-AHU01}; W='C:\agentwork\ebo'; T=$(mktemp -d)
run(){ local o; o=$("$E" run "$1" "${2:-400}"); case "$o" in *EXC:*|*TIMEOUT*) printf '%s\n' "$o" | tail -12; echo "deploy_fuxa: stopped at this step"; exit 1;; esac; printf '%s\n' "$o" | grep -E 'MISSING|group |client |deleted|IoT|MQTT client' || printf '%s\n' "$o" | tail -2; }
cd "$H"
python3 make_mqtt.py "$SRV" "$F"; python3 make_fuxa.py "$SRV" "$F"
"$E" put mqtt_points.ps1 "$W\\mqtt_points.ps1" >/dev/null
"$E" logon | tail -1
run ". $W\\mqtt_points.ps1; Ahu-MqSetup" 300
# the groups come in as an import file (AHU01-mqtt.xml): the dialog picker picks wrong rows on modules with many signals
"$E" put AHU01-mqtt.xml "$W\\AHU01-mqtt.xml" >/dev/null
run "Log (Ws-Import '$SRV/IoT/Broker' '$W\\AHU01-mqtt.xml')" 300
sleep 5
"$E" mqtt 25 > "$T/broker.txt" </dev/null || true
python3 make_mqtt.py --seen "$T/broker.txt" || echo "deploy_fuxa: not every topic arrived (list above); FUXA is loaded anyway"
"$E" fuxa AHU01.fuxa.json
rm -rf "$T"
echo "done: on the EBO machine, $E run \"Log (Web-Top 'http://127.0.0.1:1881/' 'FUXA' 0 0 1600 1000)\""
