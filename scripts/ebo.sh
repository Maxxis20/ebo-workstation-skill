#!/usr/bin/env bash
# ebo.sh - host side of the EBO driver.
#   ebo.sh setup                 push win/*.ps1 to the VM and register scheduled task EboAgent (once, and after edits)
#   ebo.sh logon                 start WorkStation if needed and log on (password from the environment, see below)
#   ebo.sh run '<powershell>' [seconds]   run PowerShell in the console session with lib.ps1 + ebo.ps1 loaded, print its output
#   ebo.sh put <local> <win path> | get <win path> <local> | shot [png] | sys '<powershell>' (as SYSTEM, session 0)
#   ebo.sh mqtt [seconds]        everything the broker on the VM receives in that time (default 12), as "topic payload" lines
#   ebo.sh fuxa <project.json>   load a FUXA project into the FUXA on the VM (http://127.0.0.1:1881/)
#
# Environment: EBO_PVE_SSH (ssh target of the Proxmox node, e.g. root@pve1), EBO_VMID, optionally EBO_PVE_NODE.
#   Another hypervisor: point EBO_PS at a program that takes one PowerShell string and runs it in the guest as
#   SYSTEM, and EBO_SHOT at one that takes an optional png path and writes a console screenshot there.
#   Log-on: EBO_ADMIN_PASSWORD in the environment of this script. Better: leave it out of your shell and set
#   EBO_SECRET_RUN to your secret manager's runner (e.g. "op run --"), which is put in front of the one child
#   process that reads the password. EBO_ADMIN_USER (default admin) = WorkStation user, EBO_WIN_USER (default
#   admin) = the Windows account whose console session WorkStation runs in.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd)
sys(){ "${EBO_PS:-$S/transport/proxmox-ps.sh}" "$1" </dev/null; }      # </dev/null: ssh would otherwise eat the stdin of a calling loop
put(){ local b64 n i=0 step=7000; b64=$(base64 < "$1" | tr -d '\n'); n=${#b64}
  sys "Remove-Item -Force '$2.b64' -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force (Split-Path '$2') | Out-Null" >/dev/null
  while [ $i -lt $n ]; do sys "[IO.File]::AppendAllText('$2.b64','${b64:$i:$step}')" >/dev/null; i=$((i+step)); done
  sys "[IO.File]::WriteAllBytes('$2',[Convert]::FromBase64String([IO.File]::ReadAllText('$2.b64'))); Remove-Item '$2.b64'; (Get-Item '$2').Length"; }
get(){ local n i=0 step=60000; : > "$2.b64"
  n=$(sys "[Convert]::ToBase64String([IO.File]::ReadAllBytes('$1')).Length" | tr -d '\r\n ')
  while [ "$i" -lt "$n" ]; do sys "\$b=[Convert]::ToBase64String([IO.File]::ReadAllBytes('$1')); \$b.Substring($i,[Math]::Min($step,\$b.Length-$i))" | tr -d '\r\n' >> "$2.b64"; i=$((i+step)); done
  base64 -d < "$2.b64" > "$2"; rm -f "$2.b64"; wc -c < "$2"; }
case "${1:-}" in
  setup)
    for f in lib.ps1 agent.ps1 agent.vbs ebo.ps1 timer.ps1; do [ -f "$S/win/$f" ] && put "$S/win/$f" "C:\\agentwork\\ebo\\$f" >/dev/null; done
    sys "\$a=New-ScheduledTaskAction -Execute wscript.exe -Argument 'C:\\agentwork\\ebo\\agent.vbs'; \$p=New-ScheduledTaskPrincipal -UserId '${EBO_WIN_USER:-admin}' -LogonType Interactive -RunLevel Highest; Register-ScheduledTask -TaskName EboAgent -Action \$a -Principal \$p -Force | % TaskName" ;;
  run)
    t=$(mktemp); printf '%s\n' "$2" > "$t"; put "$t" 'C:\agentwork\ebo\cmd.ps1' >/dev/null; rm -f "$t"
    sys "Remove-Item C:\\agentwork\\ebo\\done.txt,C:\\agentwork\\ebo\\out.txt -ErrorAction SilentlyContinue; Start-ScheduledTask EboAgent" >/dev/null
    # poll in short calls: one guest-agent call may not run longer than 120 s
    end=$(( $(date +%s) + ${3:-100} )); st=wait
    while [ "$(date +%s)" -lt "$end" ]; do
      st=$(sys "\$i=0; while(-not (Test-Path C:\\agentwork\\ebo\\done.txt) -and \$i -lt 40){ Start-Sleep -Milliseconds 500; \$i++ }; if(Test-Path C:\\agentwork\\ebo\\done.txt){'done'}else{'wait'}" | tr -d '\r\n ')
      [ "$st" = done ] && break
    done
    [ "$st" = done ] || echo TIMEOUT
    sys "Get-Content C:\\agentwork\\ebo\\out.txt -Encoding UTF8 -ErrorAction SilentlyContinue" ;;
  logon)
    # Scripted WorkStation log-on. The password goes environment of one child process -> ssh stdin -> guest agent
    # stdin -> a file on the VM that Ws-Logon reads and deletes. It is never printed and never in argv.
    # This step talks to the guest agent directly (stdin is needed), so it is Proxmox only.
    : "${EBO_PVE_SSH:?set EBO_PVE_SSH}" "${EBO_VMID:?set EBO_VMID}"
    ${EBO_SECRET_RUN:-} python3 -c '
import os
q = chr(39)
pw = os.environ["EBO_ADMIN_PASSWORD"].replace(q, q * 2)
print("[IO.File]::WriteAllText(" + q + "C:\\agentwork\\ebo\\.pw" + q + ", " + q + pw + q + ")")' 2>/dev/null \
      | ssh -o BatchMode=yes "$EBO_PVE_SSH" "qm guest exec $EBO_VMID --pass-stdin 1 --timeout 30 -- powershell.exe -NoProfile -Command -" >/dev/null 2>&1 \
      || { echo "logon: could not hand the password to the VM (is EBO_ADMIN_PASSWORD available to the child process?)"; exit 1; }
    "$0" run "try { Log (Ws-Ensure '${EBO_ADMIN_USER:-admin}') } finally { Remove-Item C:\\agentwork\\ebo\\.pw -Force -ErrorAction SilentlyContinue }" 120 ;;
  mqtt)   # mosquitto_sub -W does not end by itself under the guest agent, so a job with a deadline does the listening
    sys "\$j=Start-Job { & 'C:\\Program Files\\mosquitto\\mosquitto_sub.exe' -h 127.0.0.1 -t '#' -v }; Start-Sleep ${2:-12}; Stop-Job \$j; Receive-Job \$j; Remove-Job \$j -Force; Get-Process mosquitto_sub -ErrorAction SilentlyContinue | Stop-Process -Force" | tr -d '\r' ;;
  fuxa)
    put "$2" 'C:\agentwork\fuxa\project.json' >/dev/null
    c=$(sys "curl.exe -s -o NUL -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data-binary '@C:\agentwork\fuxa\project.json' http://127.0.0.1:1881/api/project" | tr -d '\r\n ')
    [ "$c" = 200 ] && echo "FUXA project loaded" || { echo "FUXA answered: $c"; exit 1; } ;;
  put) put "$2" "$3" ;;
  get) get "$2" "$3" ;;
  sys) sys "$2" ;;
  shot) "${EBO_SHOT:-$S/transport/proxmox-shot.sh}" ${2:+"$2"} ;;
  *) sed -n 2,9p "$0"; exit 2 ;;
esac
