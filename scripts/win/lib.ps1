# lib.ps1 - helpers for driving EBO WorkStation and the Function Block editor from your desktop session.
# Dot-sourced by cli.ps1. Everything here must run in the interactive session, not as a service.
Add-Type -AssemblyName System.Windows.Forms, UIAutomationClient, UIAutomationTypes
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public static class W32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out int pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern IntPtr GetMenu(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetMenuItemCount(IntPtr m);
  [DllImport("user32.dll")] public static extern IntPtr GetSubMenu(IntPtr m, int pos);
  [DllImport("user32.dll")] public static extern uint GetMenuItemID(IntPtr m, int pos);
  [DllImport("user32.dll")] public static extern uint GetMenuState(IntPtr m, uint id, uint flags);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetMenuString(IntPtr m, uint id, StringBuilder s, int n, uint flags);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
[void][W32]::SetProcessDPIAware()
$script:A  = [System.Windows.Automation.AutomationElement]
$script:TS = [System.Windows.Automation.TreeScope]
$script:CT = [System.Windows.Automation.ControlType]
function Log($s) { "$(Get-Date -Format HH:mm:ss.fff) $s" }

function Fg-Title { $sb = New-Object Text.StringBuilder 400; [void][W32]::GetWindowText([W32]::GetForegroundWindow(), $sb, 400); "$sb" }

# A top-level window by part of its title, optionally of one program. Process.MainWindowTitle is not reliable
# (WorkStation's goes empty after a dialog), so the desktop's children are listed through UI Automation.
function Find-Window($titlePart, $procName) {
  $ids = if ($procName) { @(Get-Process $procName -ErrorAction SilentlyContinue | % Id) } else { $null }
  if ($procName -and -not $ids) { return $null }
  foreach ($w in $A::RootElement.FindAll($TS::Children, [System.Windows.Automation.Condition]::TrueCondition)) {
    try { $c = $w.Current } catch { continue }
    if ($c.Name -like "*$titlePart*" -and (-not $ids -or $ids -contains $c.ProcessId)) {
      return [pscustomobject]@{ Id = $c.ProcessId; MainWindowHandle = [IntPtr]$c.NativeWindowHandle; MainWindowTitle = $c.Name }
    }
  }
  return $null
}

# Bring a window to the front. Windows refuses SetForegroundWindow from a background process unless that
# process has just produced input, so tap a key nothing listens to (F24) first. Not Alt: that puts the target's
# menu bar in keyboard mode and the next keys go to the menu. Last resort: minimise and restore.
# Never click the taskbar button: on a window that is already in front that minimises it.
function Fg-Pid { $id = 0; [void][W32]::GetWindowThreadProcessId([W32]::GetForegroundWindow(), [ref]$id); $id }
function Activate($titlePart, $procName) {
  $p = Find-Window $titlePart $procName
  if (-not $p) { return $false }
  $h = $p.MainWindowHandle
  if ((Fg-Pid) -eq $p.Id -and -not [W32]::IsIconic($h)) { return $true }
  if ([W32]::IsIconic($h)) { [void][W32]::ShowWindow($h, 9) }
  foreach ($try in 1..3) {
    [W32]::keybd_event(0x87, 0, 0, [UIntPtr]::Zero); [W32]::keybd_event(0x87, 0, 2, [UIntPtr]::Zero)
    [void][W32]::SetForegroundWindow($h); Start-Sleep -Milliseconds 300
    if ((Fg-Pid) -eq $p.Id) { return $true }
    if ($try -eq 2) { [void][W32]::ShowWindow($h, 6); Start-Sleep -Milliseconds 300; [void][W32]::ShowWindow($h, 9); Start-Sleep -Milliseconds 400 }
  }
  return ((Fg-Pid) -eq $p.Id)
}

function Wait-Fg($pattern, $sec = 20) {
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt $sec) { if ((Fg-Title) -match $pattern) { return $true }; Start-Sleep -Milliseconds 200 }
  return $false
}
function Wait-Window($titlePart, $procName, $sec = 30) {
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt $sec) { $p = Find-Window $titlePart $procName; if ($p) { return $p }; Start-Sleep -Milliseconds 300 }
  return $null
}

function Keys($s) { [System.Windows.Forms.SendKeys]::SendWait($s) }
function Text($s) { [System.Windows.Forms.SendKeys]::SendWait([regex]::Replace($s, '[+^%~(){}\[\]]', '{$0}')) }
function Click($x, $y, [switch]$Right) {
  [void][W32]::SetCursorPos($x, $y); Start-Sleep -Milliseconds 120
  $d, $u = 2, 4; if ($Right) { $d, $u = 8, 16 }
  [W32]::mouse_event($d, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 40; [W32]::mouse_event($u, 0, 0, 0, [UIntPtr]::Zero)
}

# ---- classic Win32 menus (the Function Block editor, tam32.exe): no focus and no coordinates needed -----------
function Menu-List($hwnd) {
  $m = [W32]::GetMenu($hwnd); $out = @()
  for ($i = 0; $i -lt [W32]::GetMenuItemCount($m); $i++) {
    $sb = New-Object Text.StringBuilder 200; [void][W32]::GetMenuString($m, $i, $sb, 200, 0x400); $top = "$sb" -replace '&', ''
    $sub = [W32]::GetSubMenu($m, $i)
    for ($j = 0; $j -lt [W32]::GetMenuItemCount($sub); $j++) {
      $sb = New-Object Text.StringBuilder 200; [void][W32]::GetMenuString($sub, $j, $sb, 200, 0x400)
      $id = [W32]::GetMenuItemID($sub, $j); $st = [W32]::GetMenuState($sub, $j, 0x400)
      if ("$sb") { $out += [pscustomobject]@{ Menu = $top; Item = ("$sb" -replace '&', '' -replace "`t.*", ''); Id = $id; Grayed = [bool]($st -band 3) } }
    }
  }
  $out
}
function Menu-Do($hwnd, $menu, $item) {
  $e = Menu-List $hwnd | ? { $_.Menu -eq $menu -and $_.Item -like $item } | select -First 1
  if (-not $e) { throw "menu item $menu > $item not found" }
  if ($e.Grayed) { throw "menu item $menu > $item is greyed out" }
  [void][W32]::PostMessage($hwnd, 0x111, [IntPtr][int]$e.Id, [IntPtr]::Zero)
}

# ---- UI Automation ---------------------------------------------------------------------------------------------
function Ui-Root($hwnd) { $A::FromHandle($hwnd) }
function Ui-Find($root, $name, $type, $sec = 8, [switch]$All) {
  $conds = @()
  if ($name) { $conds += New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, $name) }
  if ($type) { $conds += New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $type) }
  $c = if ($conds.Count -gt 1) { New-Object System.Windows.Automation.AndCondition($conds) } else { $conds[0] }
  $t = [Diagnostics.Stopwatch]::StartNew()
  do {
    if ($All) { $r = $root.FindAll($TS::Descendants, $c); if ($r.Count) { return $r } }
    else { $r = $root.FindFirst($TS::Descendants, $c); if ($r) { return $r } }
    Start-Sleep -Milliseconds 250
  } while ($t.Elapsed.TotalSeconds -lt $sec)
  return $null
}
function Ui-ById($root, $aid, $sec = 8) {
  $c = New-Object System.Windows.Automation.PropertyCondition($A::AutomationIdProperty, $aid)
  $t = [Diagnostics.Stopwatch]::StartNew()
  do { $r = $root.FindFirst($TS::Descendants, $c); if ($r) { return $r }; Start-Sleep -Milliseconds 250 } while ($t.Elapsed.TotalSeconds -lt $sec)
  return $null
}
function Ui-Invoke($el) { $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
function Ui-SetValue($el, $v) { $el.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($v) }
function Ui-Center($el) { $r = $el.Current.BoundingRectangle; [int]($r.X + $r.Width / 2), [int]($r.Y + $r.Height / 2) }
function Ui-Click($el, [switch]$Right) { $x, $y = Ui-Center $el; Click $x $y -Right:$Right }
function Ui-Dump($root, $max = 300) {
  $n = 0
  foreach ($e in $root.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)) {
    $c = $e.Current
    if ($c.Name -or $c.AutomationId) { "{0,-12} [{1}] aid={2} cls={3}" -f $c.ControlType.ProgrammaticName.Replace('ControlType.', ''), $c.Name, $c.AutomationId, $c.ClassName; $n++ }
    if ($n -ge $max) { break }
  }
}

# A top-level window or dialog of a process, by title (dialogs are not always the MainWindow).
function Top-Window($title, $sec = 10) {
  $c = New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, $title)
  $t = [Diagnostics.Stopwatch]::StartNew()
  do { $r = $A::RootElement.FindFirst($TS::Children, $c); if ($r) { return $r }
       foreach ($w in $A::RootElement.FindAll($TS::Children, [System.Windows.Automation.Condition]::TrueCondition)) { $d = $w.FindFirst($TS::Children, $c); if ($d) { return $d } }
       Start-Sleep -Milliseconds 250 } while ($t.Elapsed.TotalSeconds -lt $sec)
  return $null
}

# Standard Windows file dialog: it opens with the focus in the File name box, so type the path and press Enter.
# (The box is a combo box whose edit does not take a UI Automation value.)
function FileDialog-Set($title, $path) {
  $pat = "^" + [regex]::Escape($title) + "$"
  if (-not (Wait-Fg $pat 6)) {
    # The dialog can open behind its owner and never get the focus (seen with the editor's Import): bring it forward.
    $d = Top-Window $title 4
    if ($d) {
      [W32]::keybd_event(0x87, 0, 0, [UIntPtr]::Zero); [W32]::keybd_event(0x87, 0, 2, [UIntPtr]::Zero)
      [void][W32]::SetForegroundWindow([IntPtr]$d.Current.NativeWindowHandle)
    }
    if (-not (Wait-Fg $pat 5)) { throw "file dialog '$title' did not come to the front (foreground: $(Fg-Title))" }
  }
  Start-Sleep -Milliseconds 400; Keys '%n'; Start-Sleep -Milliseconds 150; Text $path; Start-Sleep -Milliseconds 200; Keys '{ENTER}'
}
