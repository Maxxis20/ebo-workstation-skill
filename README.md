# ebo-workstation: a Claude skill for Schneider EcoStruxure Building Operation

Lets an AI coding agent (Claude Code) program EBO 7.1 for you: you describe the plant, the agent writes the
Function Block program, loads it into the Enterprise Server through WorkStation, compiles it, binds it, draws an
operator graphic and can publish values over MQTT. It works the real WorkStation through its user interface, the
same dialogs you would click.

What is in the skill:

- `reference/findings.md`: how WorkStation and the Function Block editor behave when driven from outside, the
  `.aut` program text format with its traps, bindings, graphics (TGML), MQTT.
- `scripts/ebo.sh` + `scripts/win/`: the driver. Runs PowerShell in the VM's console session, drives WorkStation
  by UI Automation.
- `scripts/aut.py`: Function Block program generator with automatic layout and wire routing.
- `scripts/tgml.py`: graphic (HMI) generator. `scripts/fuxa.py`: FUXA project generator for an MQTT view.

## Install

```bash
git clone https://github.com/Maxxis20/ebo-workstation-skill ~/.claude/skills/ebo-workstation
```

Or into one project: clone to `<project>/.claude/skills/ebo-workstation`. Claude Code picks it up at the next
start; ask it something like "build a Function Block program in EBO that ..." and it loads the skill.

## What you need

- A Proxmox VE node you can reach with ssh keys, and on it a Windows 11 VM with the QEMU guest agent.
- EcoStruxure Building Operation 7.1.1 on that VM, Enterprise Server and WorkStation, **with a valid licence**.
  Use a test machine, never a production server: the driver creates and deletes objects under `/Server 1` and
  types into whatever window is in front.
- On your own machine: bash, ssh, Python 3 with Pillow (`pip install pillow`).
- For the MQTT part only, on the same VM: Mosquitto on `127.0.0.1:1883`, and FUXA on `http://127.0.0.1:1881/` if
  you want the web view. Notes in the findings, section MQTT.

Another hypervisor works if you supply two small programs, see the head of `scripts/ebo.sh`.

## Prepare the VM, once

1. Let the Windows account log on at the console by itself (autologon). WorkStation needs a desktop, and the
   driver works in that console session. Do not use RDP while the driver runs: it takes the session away.
2. Set the console resolution to 1600x1200 (Windows display settings).
3. Register a task that starts WorkStation in that session (PowerShell as administrator, your account name in
   place of `admin`):

   ```powershell
   $d = 'C:\Program Files (x86)\Schneider Electric EcoStruxure\Building Operation 7.1\WorkStation'
   $a = New-ScheduledTaskAction -Execute "$d\SE.SBO.WorkStation.exe" -WorkingDirectory $d
   $p = New-ScheduledTaskPrincipal -UserId admin -LogonType Interactive
   Register-ScheduledTask -TaskName EboWorkStation -Action $a -Principal $p
   ```
4. Log on to WorkStation once by hand, open any Function Block program and switch `Show Classic Mode` on. It
   stays on.

## Set-up on your machine

```bash
export EBO_PVE_SSH=root@your-proxmox-node EBO_VMID=123     # put these in your shell profile
E=~/.claude/skills/ebo-workstation/scripts/ebo.sh
$E sys 'hostname'                 # the guest agent answers
$E setup                          # driver files onto the VM, scheduled task EboAgent
$E get 'C:\Program Files (x86)\Schneider Electric EcoStruxure\Building Operation 7.1\WorkStation\MentaBlocks.xml' \
       ~/.claude/skills/ebo-workstation/reference/MentaBlocks.xml     # the editor's block catalogue, from your own installation
EBO_SECRET_RUN="op run --" $E logon      # or EBO_ADMIN_PASSWORD in the environment of this one command
$E shot now.png                   # look at the console
```

`EBO_WIN_USER` (default `admin`) is the Windows account, `EBO_ADMIN_USER` (default `admin`) the WorkStation user.
Keep the WorkStation password out of the agent's sight: `EBO_SECRET_RUN` puts your secret manager's runner in
front of the one process that reads it.

First test, by hand or by asking the agent:

```bash
$E put ~/.claude/skills/ebo-workstation/examples/blink.aut 'C:\agentwork\ebo\blink.aut'
$E run "Fb-Load '/Server 1' 'Blink' 'C:\agentwork\ebo\blink.aut'" 150
$E shot blink.png
```

## Limits, plainly

- Proven on one installation: EBO 7.1.1.132, English, 1600x1200. WorkStation is driven through UI Automation
  names and menu command ids where it offers them, and through a few fixed screen positions where it does not.
  Another version or language will break some of it; the findings say where each fact came from.
- The WorkStation automation API would be the proper way in. It needs an SDK licence key, and this skill does
  not work around that.
- One command at a time, and nobody else on the console while it runs.
- Slow where the user interface is slow: about 10 s per MQTT data point, about 6 s per bound point.
- The engineering is still yours: check what the agent built before it goes anywhere near a real plant.

## Not affiliated

An independent project, not made, endorsed or supported by Schneider Electric. EcoStruxure, Building Operation
and Menta are trademarks of Schneider Electric. No Schneider software or files are included; you need your own
licensed installation.

MIT licence.
