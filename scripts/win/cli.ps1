# cli.ps1 - the driver's entry point on the Windows machine that runs EBO. Called by ../ebo.sh, or directly:
#   powershell -NoProfile -ExecutionPolicy Bypass -File cli.ps1 <verb> [arg1] [arg2]
# Verbs: check | setup | run <file.ps1> | put <from> <to> | get <from> <to> | shot [png] | logon [user] | mqtt [seconds] | fuxa <project.json>
# Must run in your own desktop session (it works WorkStation's windows), not as a service.
param([string]$Verb = '', [string]$A1 = '', [string]$A2 = '')
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$work = 'C:\agentwork\ebo'
$ebo  = 'C:\Program Files (x86)\Schneider Electric EcoStruxure\Building Operation 7.1'
$cat  = Join-Path (Split-Path -Parent (Split-Path -Parent $here)) 'reference\MentaBlocks.xml'
function Load-Driver { . "$here\lib.ps1"; . "$here\ebo.ps1" }
switch ($Verb) {
  'setup' {
    New-Item -ItemType Directory -Force $work | Out-Null
    Copy-Item "$here\timer.ps1" $work -Force
    "work folder $work ready"
    # The block catalogue is Schneider's file: it is taken from this machine's own installation, never shipped.
    if (Test-Path $cat) { 'block catalogue already in reference' }
    elseif (Test-Path "$ebo\WorkStation\MentaBlocks.xml") { Copy-Item "$ebo\WorkStation\MentaBlocks.xml" $cat; 'block catalogue copied from your installation' }
    else { "block catalogue NOT found at $ebo\WorkStation\MentaBlocks.xml: copy MentaBlocks.xml into the skill's reference folder by hand" }
  }
  'check' {
    # What is ready and what is not, one line each: OK / TODO (the agent or the user can fix it) / INFO.
    . "$here\lib.ps1"; . "$here\ebo.ps1"
    if (Test-Path "$ebo\WorkStation\SE.SBO.WorkStation.exe") { 'OK    EBO 7.1 WorkStation is installed' }
    else {
      $other = @(Get-ChildItem 'C:\Program Files (x86)\Schneider Electric EcoStruxure' -Directory -ErrorAction SilentlyContinue | % Name) -join ', '
      "TODO  EBO 7.1 WorkStation not found at $ebo (found: $(if ($other) { $other } else { 'nothing' })). This skill was made on 7.1.1."
    }
    $svc = Get-Service | ? { $_.DisplayName -like 'Building Operation*Enterprise Server*' } | select -First 1
    if (-not $svc) { 'TODO  no Enterprise Server service on this machine: programs are created under /Server 1 of a local Enterprise Server' }
    elseif ($svc.Status -ne 'Running') { "TODO  Enterprise Server service is $($svc.Status): start it (needs administrator rights): $($svc.DisplayName)" }
    else { 'OK    Enterprise Server service is running' }
    if (Test-Path $work) { "OK    work folder $work" } else { "TODO  work folder missing: run ebo.sh setup" }
    if (Test-Path $cat) { 'OK    block catalogue reference\MentaBlocks.xml' } else { 'TODO  block catalogue missing: run ebo.sh setup (copies it from the installation)' }
    if (-not (Ws-Proc)) { 'TODO  WorkStation is not running: run ebo.sh logon (starts it and asks the user for the password in a Windows box)' }
    elseif (Ws-LoggedOn) { 'OK    WorkStation is running and logged on' }
    else { 'TODO  WorkStation is logged off: run ebo.sh logon (the user types the password in a Windows box)' }
    'INFO  Classic Mode cannot be seen from outside. If Fb-Load says "is Classic Mode on?": ask the user to open any Function Block program in WorkStation and switch "Show Classic Mode" on, once.'
    Add-Type -AssemblyName System.Drawing
    $g = [Drawing.Graphics]::FromHwnd([IntPtr]::Zero); $dpi = [int]$g.DpiX; $g.Dispose()
    $b = [Windows.Forms.Screen]::PrimaryScreen.Bounds
    if ($dpi -eq 96) { "OK    display scaling 100 %, screen $($b.Width)x$($b.Height)" }
    else { "INFO  display scaling is $([int]($dpi / 0.96)) %, screen $($b.Width)x$($b.Height). The driver was measured at 100 %: if clicks land beside their target, ask the user to set scaling to 100 %." }
    if ($b.Width -lt 1280 -or $b.Height -lt 800) { 'INFO  small screen: the editors may not fit' }
    $py = @('python', 'python3', 'py') | ? { (Get-Command $_ -ErrorAction SilentlyContinue) -and ("$(try { & $_ --version 2>&1 } catch { '' })" -match '^Python 3') } | select -First 1   # the Store stub named python.exe does not count
    if ($py) { "OK    Python ($py)" } else { 'TODO  Python 3 not found: the generators (aut.py, tgml.py, fuxa.py) need it' }
    if (Test-Path 'C:\Program Files\mosquitto\mosquitto_sub.exe') { 'OK    Mosquitto installed (MQTT part)' } else { 'INFO  Mosquitto not installed: only needed for MQTT' }
    $t = New-Object Net.Sockets.TcpClient; try { $t.Connect('127.0.0.1', 1881); 'OK    FUXA answers on 127.0.0.1:1881' } catch { 'INFO  no FUXA on 127.0.0.1:1881: only needed for the web view' } finally { $t.Close() }
  }
  'run' {
    . "$here\lib.ps1"; . "$here\ebo.ps1"
    try { & $A1 *>&1 | % { ($_ | Out-String -Width 400).TrimEnd() } }
    catch { "EXC: $($_.Exception.Message)`n$($_.ScriptStackTrace)" }
  }
  'put' { New-Item -ItemType Directory -Force (Split-Path $A2) | Out-Null; Copy-Item $A1 $A2 -Force; (Get-Item $A2).Length }
  'get' { Copy-Item $A1 $A2 -Force; (Get-Item $A2).Length }
  'shot' {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    Add-Type -Namespace Cli -Name Dpi -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();'
    [void][Cli.Dpi]::SetProcessDPIAware()
    if (-not $A1) { $A1 = Join-Path $env:TEMP ("ebo-" + (Get-Date -Format HHmmss) + ".png") }
    $b = [Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object Drawing.Bitmap $b.Width, $b.Height
    $g = [Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Location, [Drawing.Point]::Empty, $b.Size); $g.Dispose()
    $bmp.Save($A1, [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
    $A1
  }
  'logon' {
    # The password comes from the environment of this process, or from a Windows credential box, and goes into a file that Ws-Logon reads and deletes.
    # It is never printed and never on a command line.
    . "$here\lib.ps1"; . "$here\ebo.ps1"
    New-Item -ItemType Directory -Force $work | Out-Null
    $user = if ($A1) { $A1 } else { 'admin' }
    if ($env:EBO_ADMIN_PASSWORD) { [IO.File]::WriteAllText("$work\.pw", $env:EBO_ADMIN_PASSWORD) }
    elseif (-not ((Ws-Proc) -and (Ws-LoggedOn))) {
      # Nothing in the environment: ask the person at the machine, in a Windows credential box. The agent never sees it.
      $c = Get-Credential -UserName $user -Message 'EBO WorkStation log-on for the driver. The password stays on this machine.'
      if ($c) { [IO.File]::WriteAllText("$work\.pw", $c.GetNetworkCredential().Password) }
    }
    try { Log (Ws-Ensure $user) }
    catch { if ("$($_.Exception.Message)" -eq 'no password file') { 'logon: no password given. Log on to WorkStation by hand, or run this again and fill in the box.' } else { "EXC: $($_.Exception.Message)" } }
    finally { Remove-Item "$work\.pw" -Force -ErrorAction SilentlyContinue }
  }
  'mqtt' {
    $sec = if ($A1) { [int]$A1 } else { 12 }
    $j = Start-Job { & 'C:\Program Files\mosquitto\mosquitto_sub.exe' -h 127.0.0.1 -t '#' -v }
    Start-Sleep $sec; Stop-Job $j; Receive-Job $j; Remove-Job $j -Force
    Get-Process mosquitto_sub -ErrorAction SilentlyContinue | Stop-Process -Force
  }
  'fuxa' {
    $c = & curl.exe -s -o NUL -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data-binary "@$A1" http://127.0.0.1:1881/api/project
    if ("$c".Trim() -eq '200') { 'FUXA project loaded' } else { "FUXA answered: $c"; exit 1 }
  }
  default { 'verbs: check | setup | run <file.ps1> | put <from> <to> | get <from> <to> | shot [png] | logon [user] | mqtt [seconds] | fuxa <project.json>'; exit 2 }
}
