#!/usr/bin/env bash
# deploy.sh [server path] [folder]  - build everything and put AHU01 on an EBO server, bound and running against
# the plant simulation: programs AHU and SIM, graphic, trend logs, dashboard, weekly schedules.
# About 6 minutes. Needs the ebo-workstation skill driver (ebo.sh) and a logged-on WorkStation.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); S=$H/../../scripts; E=$S/ebo.sh
SRV=${1:-/Server 1}; F=${2:-AHU01}; W='C:\agentwork\ebo'; T=$(mktemp -d)
run(){ local o; o=$("$E" run "$1" "${2:-400}"); case "$o" in *EXC:*|*TIMEOUT*) printf '%s\n' "$o" | tail -12; echo "deploy: stopped at this step"; exit 1;; esac; printf '%s\n' "$o" | tail -2; }
cd "$H"
python3 make_program.py >/dev/null; python3 make_sim.py >/dev/null; python3 make_hmi.py --bench >/dev/null
python3 make_dashboard.py "$SRV/$F" >/dev/null; python3 make_binds.py "$SRV" "$F"
for f in AHU01.aut AHU01-SIM.aut AHU01-HMI.tgml AHU01-objects.xml; do "$E" put "$f" "$W\\$f" >/dev/null; done
"$E" logon | tail -1
# a WebStation window opened by Web-Station stays on top of WorkStation and hides it from the driver: close it first
"$E" run "Get-Process msedge -ea 0 | ? { \$_.MainWindowTitle -match 'Building Operation' } | % { [void]\$_.CloseMainWindow() }; Log 'WebStation window closed'" 40 >/dev/null
run "Log ('SIM: ' + (Fb-Check '$W\\AHU01-SIM.aut')); Log ('AHU: ' + (Fb-Check '$W\\AHU01.aut'))" 200
"$E" logon | tail -1          # again: the compile check runs outside WorkStation, which logs off after 5 idle minutes
run "try { Log (Ws-Delete '$SRV/$F') } catch { Log 'no earlier folder of that name' }; Log (Ws-New '$SRV' 'Folder' '$F'); Fb-Load '$SRV/$F' 'SIM' '$W\\AHU01-SIM.aut'" 400
run "Fb-Load '$SRV/$F' 'AHU' '$W\\AHU01.aut'" 400
run "Gfx-Load '$SRV/$F' 'Graphic' '$W\\AHU01-HMI.tgml'" 400
run "Log (Ws-Import '$SRV/$F' '$W\\AHU01-objects.xml'); Log (Ws-Export '$SRV/$F' '$W\\$F-all.xml' 'Special')" 400
"$E" get "$W\\$F-all.xml" "$T/all.xml" >/dev/null
python3 "$S/ebox.py" bind "$T/all.xml" "$T/bound.xml" binds.json "$SRV"
"$E" put "$T/bound.xml" "$W\\$F-bound.xml" >/dev/null
run "Log (Ws-Delete '$SRV/$F'); Log (Ws-Import '$SRV' '$W\\$F-bound.xml')" 400
rm -rf "$T"
echo "done: open $SRV/$F/Graphic, press Reset once (latches from the moment before the bindings existed)."
