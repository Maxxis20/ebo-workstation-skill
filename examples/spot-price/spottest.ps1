# spottest.ps1 - test scenarios for the spot price example, run in the WorkStation desktop session (ebo.sh run).
# The bridge (spotd.py, fake source) runs from $SpotDir with a portable Python; the broker is the one on this machine.
# Scn <name> <actions>: records the program's MQTT trace (topic 'Server 1/<folder>/SPOT/#') with its time while it
# plays the actions. The graphic is found on the screen by its dark header (so the crops hold whatever the user's
# WorkStation layout: a docked Alarms pane makes WorkStation scale the graphic down), and the Alarm View positions
# follow the same left shift.
#   @(s, 'fake', <file>)          write fake\<file>.json as the bridge's fake.json (moves its clock, prices, dead)
#   @(s, 'set', <Set name>, <v>)  write an operator setting through the Test client's subscription
#   @(s, 'stop') / @(s, 'start')  stop / start the bridge
#   @(s, 'shot', <name>)          screenshot of the graphic (cropped to it)
#   @(s, 'alarms', <name>)        open the Alarm View <folder>/AlarmList, filter it, screenshot, back to the graphic
#   @(s, 'end')
# Output: C:\agentwork\ebo\spot\<name>.txt (trace) and <name>.act (actions, same clock). The crops assume the
# WorkStation window maximised on a 1600x1200 screen, System Tree docked left.
# (No variable named $a, $ts or $ct here: PowerShell names ignore case and the driver keeps $A, $TS, $CT.)
$SpotDir = 'C:\agentwork\spot'; $TestDir = 'C:\agentwork\ebo\spot'
$Py = 'C:\agentwork\python\python.exe'
$Sub = 'C:\Program Files\mosquitto\mosquitto_sub.exe'; $Pub = 'C:\Program Files\mosquitto\mosquitto_pub.exe'
$GfxRect = @(265, 220, 1335, 892); $XOff = 0          # found again by Spot-Layout at the start of every scenario
function Spot-Layout {
  # find the graphic: its header is #1F2933 across its full width; WorkStation shows the 1300 x 880 graphic scaled
  Add-Type -AssemblyName System.Windows.Forms, System.Drawing
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  $hd = { param($x, $y) $c = $bmp.GetPixel($x, $y); [Math]::Abs($c.R - 31) + [Math]::Abs($c.G - 41) + [Math]::Abs($c.B - 51) -lt 12 }
  $top = $null; foreach ($y in 150..500) { if (& $hd 900 $y) { $top = $y; break } }
  if ($null -eq $top) { $g.Dispose(); $bmp.Dispose(); throw 'graphic header not found on the screen' }
  $yy = $top + 3; $left = 900; while ($left -gt 0 -and (& $hd ($left - 1) $yy)) { $left-- }
  $right = 900; while ($right -lt $b.Width - 1 -and (& $hd ($right + 1) $yy)) { $right++ }
  $g.Dispose(); $bmp.Dispose()
  $w = $right - $left + 1
  $script:GfxRect = @($left, $top, $w, [int][Math]::Round(880 * $w / 1300))
  $script:XOff = $left - 265                      # 0 with the layout the coordinates below were taken at
  "graphic at $($script:GfxRect -join ',')"
}
function Now-Unix { [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0 }
function Spot-Stop {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? { $_.CommandLine -like '*spotd.py*' } |
    % { Stop-Process -Id $_.ProcessId -Force }
}
function Spot-Start {
  Spot-Stop
  Start-Process $Py -ArgumentList "spotd.py config.json" -WorkingDirectory $SpotDir -WindowStyle Hidden `
    -RedirectStandardOutput "$SpotDir\spotd.log" -RedirectStandardError "$SpotDir\spotd.err"
}
function Spot-Fake($file) {      # new content and a new write time: the bridge reads the file again when it changes
  [IO.File]::WriteAllText("$SpotDir\fake.json", [IO.File]::ReadAllText("$SpotDir\fake\$file.json"))
}
function Spot-Set($folder, $name, $value) {
  $f = "$TestDir\msg.json"
  [IO.File]::WriteAllText($f, '{"pointId":"/Server 1/' + $folder + '/Set/' + $name + '/Value","value":' + $value + '}')
  & $Pub -h 127.0.0.1 -t spotprice/cmd -f $f
}
function Spot-Shot($file, $r = $script:GfxRect) {
  Add-Type -AssemblyName System.Windows.Forms, System.Drawing
  $bmp = New-Object System.Drawing.Bitmap $r[2], $r[3]
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen((New-Object System.Drawing.Point $r[0], $r[1]), [System.Drawing.Point]::Empty,
                    (New-Object System.Drawing.Size $r[2], $r[3]))
  $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
}
function Spot-Alarms($folder, $file) {
  Ws-Open "/Server 1/$folder/AlarmList"; Start-Sleep 3
  $o = $script:XOff
  Click (735 + $o) 205; Keys '^a'; Text $folder; Start-Sleep 2    # quick filter: only this folder's alarms
  $L = 265 + $o; $bx = [int]($L + 703 * (1580 - $L) / 1315)       # columns scale with the width of the view
  Drag $bx 237 ($bx + 320) 237; Start-Sleep 1                     # widen the Alarm text column
  Spot-Shot $file @((265 + $o), 160, 1335, 240)    # (the comma binds before +)
  Tab-Close 'AlarmList'
  Ws-Open "/Server 1/$folder/Graphic"; Start-Sleep 2
}
function Scn($name, $acts, $folder = 'SpotPrice') {
  New-Item -ItemType Directory -Force $TestDir | Out-Null
  Get-Process mosquitto_sub -ErrorAction SilentlyContinue | Stop-Process -Force
  $out = "$TestDir\$name.txt"; $act = "$TestDir\$name.act"
  Remove-Item $out, $act, "$TestDir\$name-*.png" -ErrorAction SilentlyContinue
  $p = Start-Process $Sub -ArgumentList "-h 127.0.0.1 -t `"Server 1/$folder/SPOT/#`" -t `"spot/FI/now`" -F `"%I %t %p`"" `
       -RedirectStandardOutput $out -PassThru -WindowStyle Hidden
  Start-Sleep 2
  Add-Content $act "$(Now-Unix) layout $(Spot-Layout)"
  $t0 = Get-Date
  foreach ($step in $acts) {
    $due = $t0.AddSeconds($step[0]); $w = ($due - (Get-Date)).TotalMilliseconds
    if ($w -gt 0) { Start-Sleep -Milliseconds $w }
    $u = Now-Unix
    switch ($step[1]) {
      'fake'   { Spot-Fake $step[2]; Add-Content $act "$u fake $($step[2])" }
      'set'    { Spot-Set $folder $step[2] $step[3]; Add-Content $act "$u set $($step[2]) $($step[3])" }
      'stop'   { Spot-Stop; Add-Content $act "$u bridge stop" }
      'start'  { Spot-Start; Add-Content $act "$u bridge start" }
      'shot'   { Spot-Shot "$TestDir\$name-$($step[2]).png"; Add-Content $act "$u shot $($step[2])" }
      'alarms' { try { Spot-Alarms $folder "$TestDir\$name-$($step[2]).png"; Add-Content $act "$u alarms $($step[2])" }
                 catch { Add-Content $act "$u alarms-failed $($step[2]) $($_.Exception.Message -replace '\s+',' ')" } }
      'end'    { Add-Content $act "$u end" }
    }
  }
  Start-Sleep 1; Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  "$name : $((Get-Content $out -ErrorAction SilentlyContinue).Count) trace lines, $((Get-Content $act).Count) actions"
}
