#!/usr/bin/env bash
# proxmox-shot.sh [out.png] : the VM console (what noVNC shows) as PNG through the QEMU monitor. Prints the path.
# Needs: EBO_PVE_SSH, EBO_VMID; EBO_PVE_NODE if the node name differs from the host name of the ssh target.
# Needs Pillow on this machine (pip install pillow).
set -euo pipefail
: "${EBO_PVE_SSH:?set EBO_PVE_SSH, e.g. root@pve1}" "${EBO_VMID:?set EBO_VMID}"
out=${1:-${TMPDIR:-/tmp}/vm$EBO_VMID-$(date +%H%M%S).png}
ssh -o BatchMode=yes "$EBO_PVE_SSH" "n=${EBO_PVE_NODE:-\$(hostname)}; pvesh create /nodes/\$n/qemu/$EBO_VMID/monitor --command 'screendump /tmp/vm$EBO_VMID.ppm' >/dev/null && cat /tmp/vm$EBO_VMID.ppm" \
 | python3 -c 'import sys,io,PIL.Image as I; I.open(io.BytesIO(sys.stdin.buffer.read())).save(sys.argv[1])' "$out"
echo "$out"
