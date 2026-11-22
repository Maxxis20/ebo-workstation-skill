#!/usr/bin/env bash
# ebo.sh - the EBO driver, for a bash on the Windows machine that runs EBO (Git Bash, which Claude Code uses).
#   ebo.sh check                 what is ready on this machine and what is not, one line each
#   ebo.sh setup                 make the work folder C:\agentwork\ebo and fetch the block catalogue (once)
#   ebo.sh logon                 start WorkStation if needed and log on (password from the environment, see below)
#   ebo.sh run '<powershell>' [seconds]   run PowerShell with lib.ps1 + ebo.ps1 loaded, print its output
#   ebo.sh put <local> <win path> | get <win path> <local> | shot [png] | sys '<powershell>' (plain PowerShell)
#   ebo.sh mqtt [seconds]        everything the local MQTT broker receives in that time (default 12), as "topic payload" lines
#   ebo.sh fuxa <project.json>   load a FUXA project into the local FUXA (http://127.0.0.1:1881/)
#
# Log-on: when WorkStation is logged off, `ebo.sh logon` opens a Windows credential box on the screen; the person
#   at the machine types the password there, the agent never sees it. Unattended instead: EBO_ADMIN_PASSWORD in
#   the environment of this script, or EBO_SECRET_RUN set to your secret manager's runner (e.g. "op run --"),
#   which is put in front of the one process that reads the password. EBO_ADMIN_USER (default admin) = WorkStation user.
# From PowerShell, without bash: powershell -NoProfile -ExecutionPolicy Bypass -File win\cli.ps1 <verb> ...
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd)
w(){ if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; elif command -v wslpath >/dev/null 2>&1; then wslpath -w "$1"; else printf '%s\n' "$1"; fi; }
ps(){ powershell.exe -NoProfile -ExecutionPolicy Bypass "$@" </dev/null | tr -d '\r'; }      # </dev/null: keeps the stdin of a calling loop
cli(){ ps -File "$(w "$S/win/cli.ps1")" "$@"; }
tmp(){ local t; t=$(mktemp); mv "$t" "$t.ps1"; printf '\xef\xbb\xbf%s\n' "$1" > "$t.ps1"; echo "$t.ps1"; }   # with BOM: Windows PowerShell reads it as UTF-8
case "${1:-}" in
  setup) cli setup ;;
  check) cli check ;;
  run)   t=$(tmp "$2")
         if command -v timeout >/dev/null 2>&1; then timeout "${3:-100}" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(w "$S/win/cli.ps1")" run "$(w "$t")" </dev/null | tr -d '\r' || { [ "${PIPESTATUS[0]}" = 124 ] && echo TIMEOUT; }
         else cli run "$(w "$t")"; fi; rm -f "$t" ;;
  sys)   t=$(tmp "$2"); ps -File "$(w "$t")" || true; rm -f "$t" ;;
  logon) ${EBO_SECRET_RUN:-} powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(w "$S/win/cli.ps1")" logon "${EBO_ADMIN_USER:-admin}" </dev/null | tr -d '\r' ;;
  put)   case "$3" in [A-Za-z]:*) cli put "$(w "$2")" "$3" ;; *) cli put "$(w "$2")" "$(w "$3")" ;; esac ;;
  get)   cli get "$2" "$(w "$3")" ;;
  shot)  if [ -n "${2:-}" ]; then cli shot "$(w "$2")" >/dev/null && echo "$2"; else cli shot; fi ;;
  mqtt)  cli mqtt "${2:-12}" ;;
  fuxa)  cli fuxa "$(w "$2")" ;;
  *) sed -n 2,10p "$0"; exit 2 ;;
esac
