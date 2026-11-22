#!/usr/bin/env bash
# proxmox-ps.sh '<powershell>' : run PowerShell inside the Windows guest through the QEMU guest agent, as SYSTEM.
# Needs: EBO_PVE_SSH (ssh target of the Proxmox node that runs the VM, e.g. root@pve1), EBO_VMID.
# Prints stdout, then stderr; exit code = guest exit code. One call may not run longer than 120 s.
set -euo pipefail
: "${EBO_PVE_SSH:?set EBO_PVE_SSH, e.g. root@pve1}" "${EBO_VMID:?set EBO_VMID}"
b64=$(printf '%s' "$1" | iconv -f utf-8 -t utf-16le | base64 | tr -d '\n')
ssh -o BatchMode=yes "$EBO_PVE_SSH" "qm guest exec $EBO_VMID --timeout 120 -- powershell -NoProfile -NonInteractive -EncodedCommand $b64" \
 | python3 -c '
import sys,json; d=json.load(sys.stdin)
sys.stdout.write(d.get("out-data","")); e=d.get("err-data","")
e="\n".join(l for l in e.splitlines() if not l.startswith("#< CLIXML") and not l.startswith("<Objs"))
if e.strip(): sys.stderr.write(e+"\n")
sys.exit(d.get("exitcode",1))'
