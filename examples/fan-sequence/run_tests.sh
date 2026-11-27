#!/usr/bin/env bash
# run_tests.sh [out dir] [test ...] - play the test scenarios on the server (after deploy.sh), fetch traces and
# screenshots, print each timeline. Tests: t1 normal start and stop, t2 requirement not met in time + Reset,
# t3 run-step requirement lost, t4 trip in run. The graphic is opened first; every test starts from Off.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); S=$H/../../scripts; E=$S/ebo.sh
OUT=${1:-$H/test-out}; shift || true; TESTS=${*:-t1 t2 t3 t4}; W='C:\agentwork\ebo'
mkdir -p "$OUT"; cd "$H"
"$E" put seqtest.ps1 "$W\\seqtest.ps1" >/dev/null
# start of every test: Off, faults off, trip released, one Reset, 4 s to settle
PRE="@(0,'pub','Mode',0),@(0,'pub','Fault_Damper',0),@(0,'pub','Fault_Fan',0),@(0,'pub','E_Stop',0),@(1,'pub','Reset',\$r),@(4,'shot','0-start')"
scn(){ case $1 in
 t1) echo "@(5,'pub','Mode',1),@(8,'shot','1-step1'),@(14,'shot','2-step2'),@(24,'shot','3-run'),@(30,'pub','Mode',0),@(35,'shot','4-step4'),@(45,'shot','5-step5'),@(62,'shot','6-idle'),@(63,'end')";;
 t2) echo "@(5,'pub','Fault_Damper',1),@(6,'pub','Mode',1),@(14,'shot','1-checking'),@(28,'shot','2-alarm'),@(30,'alarms','al1-active'),@(46,'shot','3-held'),@(48,'pub','Fault_Damper',0),@(50,'pub','Reset',(\$r+1)),@(52,'alarms','al2-reset'),@(66,'shot','4-restarted'),@(72,'shot','5-run'),@(73,'end')";;
 t3) echo "@(5,'pub','Mode',1),@(25,'shot','1-run'),@(26,'pub','Fault_Fan',1),@(29,'shot','2-lost'),@(34,'shot','3-alarm'),@(36,'alarms','al1-active'),@(60,'shot','4-stopped'),@(61,'pub','Fault_Fan',0),@(61,'pub','Mode',0),@(62,'pub','Reset',(\$r+1)),@(64,'alarms','al2-reset'),@(76,'end')";;
 t4) echo "@(5,'pub','Mode',1),@(25,'shot','1-run'),@(26,'pub','E_Stop',1),@(27,'shot','2-trip'),@(32,'shot','3-held'),@(33,'alarms','al1-active'),@(44,'pub','E_Stop',0),@(45,'pub','Reset',(\$r+1)),@(47,'alarms','al2-reset'),@(60,'shot','4-restart'),@(61,'end')";;
 esac; }
for t in $TESTS; do
  # stop phase: Off and 35 s, so that every test starts from idle (an ordered stop takes about 25 s)
  "$E" run ". $W\\seqtest.ps1; Log (Scn '$t-pre' @(@(0,'pub','Mode',0),@(35,'end')))" 120 | tail -1
  # WorkStation logs off after 5 idle minutes and a new log-on closes the graphic: log on and open it right here
  "$E" logon | tail -1
  "$E" run "Ws-Open '/Server 1/FanSeq/Graphic'; Ws-Front; Log 'graphic open'" 120 | tail -1
  "$E" run ". $W\\seqtest.ps1; \$r = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() % 100000; Log (Scn '$t' @($PRE,$(scn $t)))" 300 | tail -4
  for f in $("$E" sys "Get-ChildItem $W\\seq\\$t.txt,$W\\seq\\$t.act,$W\\seq\\$t-*.png | % Name" | tr -d '\r'); do
    "$E" get "$W\\seq\\$f" "$OUT/$f" >/dev/null
  done
  echo "== $t"; python3 analyze.py "$OUT/$t.txt" "$OUT/$t.act" | tee "$OUT/$t-timeline.txt"
done
