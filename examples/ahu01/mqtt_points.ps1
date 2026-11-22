# written by make_mqtt.py: AHU01 data points for the EBO MQTT client. Dot-source after ebo.ps1.
$MQ_IOT = '/Server 1/IoT'; $MQ_CLIENT = '/Server 1/IoT/Broker'
$MQ = [ordered]@{}
$MQ['AHU01_Meas'] = @(@(@('AHU01','AHU','Inputs'),'TE00'),@(@('AHU01','AHU','Inputs'),'TE1'),@(@('AHU01','AHU','Inputs'),'TE2'),@(@('AHU01','AHU','Inputs'),'TE3'),@(@('AHU01','AHU','Inputs'),'TE4'),@(@('AHU01','AHU','Inputs'),'TE5'),@(@('AHU01','AHU','Inputs'),'TE6'),@(@('AHU01','AHU','Inputs'),'TE7'),@(@('AHU01','AHU','Inputs'),'TE8'),@(@('AHU01','AHU','Inputs'),'TE10_1'),@(@('AHU01','AHU','Inputs'),'TE10_2'),@(@('AHU01','AHU','Inputs'),'TE10_3'),@(@('AHU01','AHU','Inputs'),'OT_Day_Mean'),@(@('AHU01','AHU','Inputs'),'Room_Avg'),@(@('AHU01','AHU','Inputs'),'PE1'),@(@('AHU01','AHU','Inputs'),'PE2'),@(@('AHU01','AHU','Inputs'),'PDE1'),@(@('AHU01','AHU','Inputs'),'PDE2'),@(@('AHU01','AHU','Inputs'),'PDE3'),@(@('AHU01','AHU','Inputs'),'PDE4'),@(@('AHU01','AHU','Inputs'),'PDE10'),@(@('AHU01','AHU','Inputs'),'PDE20'),@(@('AHU01','AHU','Inputs'),'Supply_Flow'),@(@('AHU01','AHU','Inputs'),'Exhaust_Flow'),@(@('AHU01','AHU','HRU'),'HRU_Efficiency'))
$MQ['AHU01_Ctrl'] = @(@(@('AHU01','AHU','Outputs'),'FZ01_Cmd'),@(@('AHU01','AHU','Outputs'),'FZ02_Cmd'),@(@('AHU01','AHU','Outputs'),'SC3_Ctrl'),@(@('AHU01','AHU','Outputs'),'SC3_Cmd'),@(@('AHU01','AHU','Outputs'),'TV1_Ctrl'),@(@('AHU01','AHU','Outputs'),'P1_Cmd'),@(@('AHU01','AHU','Outputs'),'TV2_Ctrl'),@(@('AHU01','AHU','Outputs'),'TF01_Ctrl'),@(@('AHU01','AHU','Outputs'),'TF01_Cmd'),@(@('AHU01','AHU','Outputs'),'PF01_Ctrl'),@(@('AHU01','AHU','Outputs'),'PF01_Cmd'),@(@('AHU01','AHU','Operation'),'Run'),@(@('AHU01','AHU','Operation'),'Run_Mode'),@(@('AHU01','AHU','Operation'),'AOM'),@(@('AHU01','AHU','Operation'),'Season_Sel'),@(@('AHU01','AHU','Operation'),'Season_Mode'),@(@('AHU01','AHU','Operation'),'Night_Cooling'),@(@('AHU01','AHU','Operation'),'Night_Heating'),@(@('AHU01','AHU','Operation'),'Heating_Mode'),@(@('AHU01','AHU','Operation'),'HS10_Ext'),@(@('AHU01','AHU','Inputs'),'P1_Fdb'),@(@('AHU01','AHU','Inputs'),'TF01_Fdb'),@(@('AHU01','AHU','Inputs'),'PF01_Fdb'),@(@('AHU01','AHU','Inputs'),'SC3_Fault'),@(@('AHU01','AHU','Inputs'),'HS10'),@(@('AHU01','AHU','Inputs'),'SB01'),@(@('AHU01','AHU','Inputs'),'FA01'),@(@('AHU01','AHU','HRU'),'Frost_Active'),@(@('AHU01','AHU','Alarms'),'Freeze_Latch'),@(@('AHU01','AHU','ST'),'Active_SP'),@(@('AHU01','AHU','FAN'),'Supply_Pressure_SP'),@(@('AHU01','AHU','FAN'),'Exhaust_Pressure_SP'),@(@('AHU01','AHU','HRU'),'PDE4_SP'))
$MQ['AHU01_Alarms'] = @(@(@('AHU01','AHU','Alarms'),'Critical_Alarm'),@(@('AHU01','AHU','Alarms'),'Freeze_Alm'),@(@('AHU01','AHU','Alarms'),'Fire_Alm'),@(@('AHU01','AHU','Alarms'),'Stop_Alm'),@(@('AHU01','AHU','Alarms'),'P1_Alm'),@(@('AHU01','AHU','Alarms'),'HN_Pres_Alm'),@(@('AHU01','AHU','Alarms'),'HN_Temp_Alm'),@(@('AHU01','AHU','Alarms'),'Supply_Fire_Alm'),@(@('AHU01','AHU','Alarms'),'Exhaust_Fire_Alm'),@(@('AHU01','AHU','Alarms'),'TE00_Alm'),@(@('AHU01','AHU','Alarms'),'TE1_Alm'),@(@('AHU01','AHU','Alarms'),'TE2_Alm'),@(@('AHU01','AHU','Alarms'),'TE3_Alm'),@(@('AHU01','AHU','Alarms'),'TE4_Alm'),@(@('AHU01','AHU','Alarms'),'TE5_Alm'),@(@('AHU01','AHU','Alarms'),'TE6_Alm'),@(@('AHU01','AHU','Alarms'),'TE7_Alm'),@(@('AHU01','AHU','Alarms'),'TE8_Alm'),@(@('AHU01','AHU','Alarms'),'TE10_1_Alm'),@(@('AHU01','AHU','Alarms'),'TE10_2_Alm'),@(@('AHU01','AHU','Alarms'),'TE10_3_Alm'),@(@('AHU01','AHU','Alarms'),'Supply_Temp_Alm'),@(@('AHU01','AHU','Alarms'),'Supply_Pres_Alm'),@(@('AHU01','AHU','Alarms'),'Exhaust_Pres_Alm'),@(@('AHU01','AHU','Alarms'),'TF01_Alm'),@(@('AHU01','AHU','Alarms'),'PF01_Alm'),@(@('AHU01','AHU','Alarms'),'HRU_Alm'),@(@('AHU01','AHU','Alarms'),'HRU_Frost_Alm'),@(@('AHU01','AHU','Alarms'),'HRU_Efficiency_Alm'),@(@('AHU01','AHU','Alarms'),'HeatR_Alm'),@(@('AHU01','AHU','Alarms'),'CoolR_Alm'),@(@('AHU01','AHU','Alarms'),'PDE3_Alm'),@(@('AHU01','AHU','Alarms'),'PDE1_Alm'),@(@('AHU01','AHU','Alarms'),'PDE2_Alm'))

# Like Dp-Pick (ebo.ps1), for modules with more rows than the picker shows: rows scrolled out of view are skipped
# instead of clicked at a position outside the list, and when no visible row matches, the selection is walked
# down with the arrow key, reading the Path box each step. The arrow-key walk is NOT yet seen working.
function Ahu-Pick($parts, $prop) {
  $d = Fg-Root; $n = $d
  $first = New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, "/$($parts[0])")), (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::TreeItem)))
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt 10 -and -not $d.FindFirst($TS::Descendants, $first)) { Start-Sleep -Milliseconds 300 }
  foreach ($p in $parts) {
    $c = New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, "/$p")), (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::TreeItem)))
    $n = $n.FindFirst($TS::Descendants, $c); if (-not $n) { Keys '{ESC}'; throw "no tree item $p" }
    try { $n.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand() } catch {}; Start-Sleep -Milliseconds 900
  }
  Ui-Click (Ui-ById $n 'objectNameTextBlock' 2); Start-Sleep -Milliseconds 1500
  $vp = $d.FindFirst($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::Edit))).GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
  $done = { Ui-Invoke (Ui-Find $d 'Select' $CT::Button 3); Start-Sleep -Milliseconds 800; "$($parts -join '/')/$prop" }
  $all = @($d.FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::DataItem))) | ? { -not $_.Current.BoundingRectangle.IsEmpty })
  $rows = @($all | ? { -not $_.Current.IsOffscreen }); if (-not $rows.Count) { $rows = $all }
  foreach ($r in $rows) {
    $b = $r.Current.BoundingRectangle
    Click ([int]($b.X + 200)) ([int]($b.Y + $b.Height / 2)); Start-Sleep -Milliseconds 150
    if (($vp.Current.Value -replace '.*/', '') -eq $prop) { return (& $done) }
  }
  if ($rows.Count) {                                          # walk on below the visible rows
    $last = $vp.Current.Value; $same = 0
    for ($i = 0; $i -lt 250 -and $same -lt 3; $i++) {
      Keys '{DOWN}'; Start-Sleep -Milliseconds 150; $v = $vp.Current.Value
      if (($v -replace '.*/', '') -eq $prop) { return (& $done) }
      if ($v -eq $last) { $same++ } else { $same = 0; $last = $v }
    }
  }
  Keys '{ESC}'; throw "property $prop not found under $($parts -join '/')"
}
# Add points to the Data Group whose page is on screen; a point that cannot be picked is reported, not fatal.
function Ahu-Points($points) {
  $script:AhuOk = 0
  foreach ($p in $points) {
    $add = Ui-ById (Prop-Grid) 'AddButton' 5; if (-not $add) { throw 'no Data points add button on this page' }
    Ws-Front; Ui-Click $add; if (-not (Wait-Fg '^Select Object' 8)) { throw 'data point picker did not open' }
    try { Log ('data point ' + (Ahu-Pick $p[0] $p[1])); $script:AhuOk++ }
    catch { Log "MISSING $($p[0] -join '/')/$($p[1]): $($_.Exception.Message)"; if (Wait-Fg '^Select Object' 1) { Keys '{ESC}'; Start-Sleep 1 } }
  }
}
# Interface and client if missing (Mq-Client sets host 127.0.0.1, no TLS, value format @(Value)); earlier AHU01
# groups are deleted, since their data points pointed at objects that deploy.sh has deleted and imported again.
function Ahu-MqSetup {
  $srv = $MQ_IOT.Substring(0, $MQ_IOT.LastIndexOf('/')); $iot = $MQ_IOT.Substring($MQ_IOT.LastIndexOf('/') + 1)
  $cl = $MQ_CLIENT.Substring($MQ_CLIENT.LastIndexOf('/') + 1); Ws-Front
  if (-not (Ws-TreeItem $MQ_IOT)) { Log (Ws-New $srv 'IoT Interface' $iot) }
  if (-not (Ws-TreeItem $MQ_CLIENT)) { Log (Mq-Client $MQ_IOT $cl) } else { Log "client $MQ_CLIENT is there" }
  foreach ($g in $MQ.Keys) { if (Ws-TreeItem "$MQ_CLIENT/$g") { Log (Ws-Delete "$MQ_CLIENT/$g") } }
}
# One chunk of one group: chunk 0 creates the group (event driven, every 10 s), later chunks add to it.
function Ahu-MqChunk($group, $chunk, $size) {
  $all = $MQ[$group]; $pts = @()
  for ($k = $chunk * $size; $k -lt [Math]::Min($all.Count, ($chunk + 1) * $size); $k++) { $pts += ,$all[$k] }
  if ($chunk -eq 0) { Log (Mq-Group $MQ_CLIENT $group @() 10) } else { [void](Ws-Select "$MQ_CLIENT/$group"); Start-Sleep 3 }
  Ahu-Points $pts
  if ($script:AhuOk) { Ws-Save }
  Log "group ${group}: chunk $chunk added $($script:AhuOk) of $($pts.Count); listed now $(@(Mq-Listed).Count) of $($all.Count)"
}

