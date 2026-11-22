#!/usr/bin/env bash
# deploy_mpc.sh [BACnet IP network path] [device name]  - AHU01 in a SpaceLogic MP-C-36A made offline:
# device, program, I/O points on terminals, input and output bindings. About 5 minutes. The BACnet Interface must
# exist on the server (New > BACnet Interface). Nothing is downloaded: the device is not connected.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); S=$H/../../scripts; E=$S/ebo.sh
NET=${1:-/Server 1/BACnet/IP Network}; DEV=${2:-AHU01-MPC}; C="$NET/$DEV"; A="$C/Application"; W='C:\agentwork\ebo'; T=$(mktemp -d)
run(){ local o; o=$("$E" run "$1" "${2:-400}"); case "$o" in *EXC:*|*TIMEOUT*) printf '%s\n' "$o" | tail -12; echo "deploy_mpc: stopped at this step"; exit 1;; esac; printf '%s\n' "$o" | tail -2; }
cd "$H"; python3 make_program.py >/dev/null
"$E" put AHU01.aut "$W\\AHU01.aut" >/dev/null; "$E" logon | tail -1
run "try { Log (Ws-Delete '$C') } catch { Log 'no earlier device of that name' }; Log (Ws-New '$NET' 'MP-C-36A' '$DEV')"
run "Fb-Load '$A' 'AHU' '$W\\AHU01.aut' 'SpaceLogic Function Block Program'"
run "Log (Ws-Export '$A/AHU' '$W\\mpc-ahu.xml' 'Special')"
"$E" get "$W\\mpc-ahu.xml" "$T/ahu.xml" >/dev/null
python3 make_controller.py "$C" "$T/ahu.xml"                # points file (outputs bound by block GUID) and input bindings
python3 "$S/ebox.py" bind "$T/ahu.xml" "$T/ahu-bound.xml" mpc_binds.json "$A"
"$E" put "$T/ahu-bound.xml" "$W\\mpc-ahu-bound.xml" >/dev/null; "$E" put AHU01-MPC-points.xml "$W\\AHU01-MPC-points.xml" >/dev/null
run "Log (Ws-Delete '$A/AHU'); Log (Ws-Import '$A' '$W\\mpc-ahu-bound.xml'); Log (Ws-Import '$A' '$W\\AHU01-MPC-points.xml')"
run "Log (Ws-Export '$C' '$W\\mpc-final.xml' 'Special')"
"$E" get "$W\\mpc-final.xml" "$T/final.xml" >/dev/null
echo "bindings in the controller: $(python3 "$S/ebox.py" binds "$T/final.xml" | grep -vc '/Alarms')  (34 terminals + 28 inputs + 11 outputs = 73 expected)"
cp "$T/final.xml" "$H/AHU01-MPC-export.xml"; rm -rf "$T"
