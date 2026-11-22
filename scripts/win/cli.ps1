# cli.ps1 - the driver's entry point on the Windows machine that runs EBO. Called by ../ebo.sh, or directly:
#   powershell -NoProfile -ExecutionPolicy Bypass -File cli.ps1 <verb> [arg1] [arg2]
# Verbs: setup | run <file.ps1> | put <from> <to> | get <from> <to> | shot [png] | logon [user] | mqtt [seconds] | fuxa <project.json>
# Must run in your own desktop session (it works WorkStation's windows), not as a service.
param([string]$Verb = '', [string]$A1 = '', [string]$A2 = '')
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$work = 'C:\agentwork\ebo'
function Load-Driver { . "$here\lib.ps1"; . "$here\ebo.ps1" }
switch ($Verb) {
  'setup' {
    New-Item -ItemType Directory -Force $work | Out-Null
    Copy-Item "$here\timer.ps1" $work -Force
    "work folder $work ready"
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
  default { 'verbs: setup | run <file.ps1> | put <from> <to> | get <from> <to> | shot [png] | logon [user] | mqtt [seconds] | fuxa <project.json>'; exit 2 }
}
