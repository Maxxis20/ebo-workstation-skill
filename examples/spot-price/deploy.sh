#!/usr/bin/env bash
# deploy.sh [server path] [folder] [area] - build the spot price example and put it on an EBO server: program SPOT,
# graphic, values (Spot, Set), bindings, MQTT clients (prices in from the bridge, test commands in, trace out),
# alarm view. About 8 minutes. The bridge itself is not part of it (tools/spotprice, run_tests.sh starts one).
# Needs the ebo-workstation skill driver (ebo.sh) and a WorkStation on the machine that runs the broker.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); S=$H/../../scripts; E=$S/ebo.sh
SRV=${1:-/Server 1}; F=${2:-SpotPrice}; AREA=${3:-FI}; W='C:\agentwork\ebo'; T=$(mktemp -d)
run(){ local o; o=$("$E" run "$1" "${2:-400}"); case "$o" in *EXC:*|*TIMEOUT*) printf '%s\n' "$o" | tail -12; echo "deploy: stopped at this step"; exit 1;; esac; printf '%s\n' "$o" | tail -2; }
cd "$H"
python3 make_program.py >/dev/null; python3 make_hmi.py "$AREA" >/dev/null; python3 make_objects.py "$SRV" "$F" --area "$AREA"
for f in Spot.aut SpotPrice.tgml SpotPrice-values.xml SpotPrice-iot.xml; do "$E" put "$f" "$W\\$f" >/dev/null; done
"$E" logon | tail -1
run "Log ('SPOT: ' + (Fb-Check '$W\\Spot.aut'))" 300
"$E" logon | tail -1
run "try { Log (Ws-Delete '$SRV/${F}_IoT') } catch { Log 'no IoT interface yet' }; try { Log (Ws-Delete '$SRV/$F') } catch { Log 'no earlier folder' }; Log (Ws-New '$SRV' 'Folder' '$F')" 300
run "Fb-Load '$SRV/$F' 'SPOT' '$W\\Spot.aut'" 600
run "Gfx-Load '$SRV/$F' 'Graphic' '$W\\SpotPrice.tgml'" 400
run "Log (Ws-Import '$SRV/$F' '$W\\SpotPrice-values.xml'); Log (Ws-Export '$SRV/$F' '$W\\$F-all.xml' 'Special')" 400
"$E" get "$W\\$F-all.xml" "$T/all.xml" >/dev/null
python3 "$S/ebox.py" bind "$T/all.xml" "$T/bound.xml" binds.json "$SRV"
python3 add_foreign.py "$T/bound.xml"          # the Special export drops Foreign addresses
"$E" put "$T/bound.xml" "$W\\$F-bound.xml" >/dev/null
run "Log (Ws-Delete '$SRV/$F'); Log (Ws-Import '$SRV' '$W\\$F-bound.xml')" 400
run "Log (Ws-Import '$SRV' '$W\\SpotPrice-iot.xml')" 300
run "Log (Ws-New '$SRV/$F' 'Alarm View' 'AlarmList')" 200
rm -rf "$T"
echo "done: open $SRV/$F/Graphic. Prices come from a bridge publishing spot/$AREA/points. Tests: ./run_tests.sh"
