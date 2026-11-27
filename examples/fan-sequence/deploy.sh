#!/usr/bin/env bash
# deploy.sh [server path] [folder] - build the fan sequence example and put it on an EBO server: program SEQ,
# graphic, command values, bindings, MQTT client (commands in, trace out). About 5 minutes.
# Needs the ebo-workstation skill driver (ebo.sh) and a WorkStation on the machine that runs the broker.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); S=$H/../../scripts; E=$S/ebo.sh
SRV=${1:-/Server 1}; F=${2:-FanSeq}; W='C:\agentwork\ebo'; T=$(mktemp -d)
run(){ local o; o=$("$E" run "$1" "${2:-400}"); case "$o" in *EXC:*|*TIMEOUT*) printf '%s\n' "$o" | tail -12; echo "deploy: stopped at this step"; exit 1;; esac; printf '%s\n' "$o" | tail -2; }
cd "$H"
python3 make_program.py >/dev/null; python3 make_hmi.py >/dev/null; python3 make_objects.py "$SRV" "$F"
for f in FanSeq.aut FanSeq.tgml FanSeq-cmd.xml FanSeq-iot.xml; do "$E" put "$f" "$W\\$f" >/dev/null; done
"$E" logon | tail -1
run "Log ('SEQ: ' + (Fb-Check '$W\\FanSeq.aut'))" 200
"$E" logon | tail -1
run "try { Log (Ws-Delete '$SRV/${F}_IoT') } catch { Log 'no IoT interface yet' }; try { Log (Ws-Delete '$SRV/$F') } catch { Log 'no earlier folder' }; Log (Ws-New '$SRV' 'Folder' '$F')" 300
run "Fb-Load '$SRV/$F' 'SEQ' '$W\\FanSeq.aut'" 400
run "Gfx-Load '$SRV/$F' 'Graphic' '$W\\FanSeq.tgml'" 400
run "Log (Ws-Import '$SRV/$F' '$W\\FanSeq-cmd.xml'); Log (Ws-Export '$SRV/$F' '$W\\$F-all.xml' 'Special')" 400
"$E" get "$W\\$F-all.xml" "$T/all.xml" >/dev/null
python3 "$S/ebox.py" bind "$T/all.xml" "$T/bound.xml" binds.json "$SRV"
"$E" put "$T/bound.xml" "$W\\$F-bound.xml" >/dev/null
run "Log (Ws-Delete '$SRV/$F'); Log (Ws-Import '$SRV' '$W\\$F-bound.xml')" 400
run "Log (Ws-Import '$SRV' '$W\\FanSeq-iot.xml')" 300
run "Log (Ws-New '$SRV/$F' 'Alarm View' 'AlarmList')" 200
rm -rf "$T"
echo "done: open $SRV/$F/Graphic. Tests: ./run_tests.sh"
