# seqtest.ps1 - test scenarios for the fan sequence, run in the WorkStation desktop session (ebo.sh run).
# Scn <name> <actions>: records every message of the program's MQTT trace (topic 'Server 1/<folder>/SEQ/#') with its
# time while it plays the actions: @(seconds, 'pub', <Cmd value name>, <value>) writes a command value through the
# MQTT client's subscription; @(seconds, 'shot', <name>) saves a screenshot of the graphic (cropped to it);
# @(seconds, 'alarms', <name>) opens the Alarm View <folder>/AlarmList, filters it to the folder, saves a screenshot
# of the list and goes back to the graphic (takes 20 to 35 s; the actions after it wait); @(seconds, 'end') stops.
# The crops assume the WorkStation window maximised on a 1600x1200 screen, System Tree docked left.
# Output: C:\agentwork\ebo\seq\<name>.txt (trace: "ISO time (1 s) topic payload") and <name>.act (actions, same clock).
$SeqDir = 'C:\agentwork\ebo\seq'
$Sub = 'C:\Program Files\mosquitto\mosquitto_sub.exe'; $Pub = 'C:\Program Files\mosquitto\mosquitto_pub.exe'
function Now-Unix { [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0 }
function Seq-Pub($folder, $name, $value) {
  $f = "$SeqDir\msg.json"
  [IO.File]::WriteAllText($f, '{"pointId":"/Server 1/' + $folder + '/Cmd/' + $name + '/Value","value":' + $value + '}')
  & $Pub -h 127.0.0.1 -t fanseq/cmd -f $f
}
$GfxRect = @(265, 220, 1335, 892)        # x, y, width, height of the graphic in the WorkStation tab
$AlmRect = @(265, 160, 1335, 240)        # the Alarm View tab: toolbar, header and the first rows
function Seq-Shot($file, $r = $GfxRect) {
  Add-Type -AssemblyName System.Windows.Forms, System.Drawing
  $bmp = New-Object System.Drawing.Bitmap $r[2], $r[3]
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen((New-Object System.Drawing.Point $r[0], $r[1]), [System.Drawing.Point]::Empty,
                    (New-Object System.Drawing.Size $r[2], $r[3]))
  $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
}
function Seq-Alarms($folder, $file) {
  Ws-Open "/Server 1/$folder/AlarmList"; Start-Sleep 3
  Click 735 205; Keys '^a'; Text $folder; Start-Sleep 2          # quick filter: only this folder's alarms
  Drag 968 237 1290 237; Start-Sleep 1                            # widen the Alarm text column to the full text
  Seq-Shot $file $AlmRect
  Tab-Close 'AlarmList'                                            # next time fresh: default widths, empty filter
  Ws-Open "/Server 1/$folder/Graphic"; Start-Sleep 2
}
# (the loop variable must not be $a: PowerShell names ignore case, and $A is the UI Automation class the driver uses)
function Scn($name, $acts, $folder = 'FanSeq') {
  New-Item -ItemType Directory -Force $SeqDir | Out-Null
  Get-Process mosquitto_sub -ErrorAction SilentlyContinue | Stop-Process -Force   # one left by a broken run writes too
  $out = "$SeqDir\$name.txt"; $act = "$SeqDir\$name.act"
  Remove-Item $out, $act, "$SeqDir\$name-*.png" -ErrorAction SilentlyContinue
  $p = Start-Process $Sub -ArgumentList "-h 127.0.0.1 -t `"Server 1/$folder/SEQ/#`" -F `"%I %t %p`"" `
       -RedirectStandardOutput $out -PassThru -WindowStyle Hidden
  Start-Sleep 2
  $t0 = Get-Date
  foreach ($step in $acts) {
    $due = $t0.AddSeconds($step[0]); $w = ($due - (Get-Date)).TotalMilliseconds
    if ($w -gt 0) { Start-Sleep -Milliseconds $w }
    $u = Now-Unix
    switch ($step[1]) {
      'pub'  { Seq-Pub $folder $step[2] $step[3]; Add-Content $act "$u pub $($step[2]) $($step[3])" }
      'shot' { Seq-Shot "$SeqDir\$name-$($step[2]).png"; Add-Content $act "$u shot $($step[2])" }
      'alarms' { try { Seq-Alarms $folder "$SeqDir\$name-$($step[2]).png"; Add-Content $act "$u alarms $($step[2])" }
                 catch { Add-Content $act "$u alarms-failed $($step[2]) $($_.Exception.Message -replace '\s+',' ')" } }
      'end'  { Add-Content $act "$u end" }
    }
  }
  Start-Sleep 1; Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  "$name : $((Get-Content $out -ErrorAction SilentlyContinue).Count) trace lines, $((Get-Content $act).Count) actions"
}
