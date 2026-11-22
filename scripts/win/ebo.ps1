# ebo.ps1 - EBO WorkStation and Function Block editor operations, on top of lib.ps1. Desktop session only.
$script:WS  = 'SE.SBO.WorkStation'
$script:FBE = 'tam32'
function Fg-Root { $A::FromHandle([W32]::GetForegroundWindow()) }
function Ws-Proc { Find-Window 'WorkStation (7' $WS }
function Ws-Root { Ui-Root (Ws-Proc).MainWindowHandle }
function Ws-Front {
  if (-not (Activate 'WorkStation (7' $WS)) { throw 'WorkStation window not brought to front' }
}
function Ws-LoggedOn { [bool](Ui-ById (Ws-Root) 'TreeView' 1) -and -not (Ui-ById (Ws-Root) 'LogOnButton' 1) }

# Log on at the WorkStation log-on screen. The password comes from C:\agentwork\ebo\.pw (written by `ebo.sh logon`
# straight from the vault) and the file is removed at once. Nothing is echoed.
function Ws-Logon($user = 'admin') {
  Ws-Front; $r = Ws-Root
  $b = Ui-ById $r 'LogOnButton' 3; if (-not $b) { return 'already logged on' }
  $f = 'C:\agentwork\ebo\.pw'; if (-not (Test-Path $f)) { throw 'no password file' }
  $pw = [IO.File]::ReadAllText($f); Remove-Item $f -Force
  $edits = Ui-Find $r $null $CT::Edit 3 -All
  Ui-Click $edits[0]; Start-Sleep -Milliseconds 300; Keys '^a'; Text $user; Keys '{TAB}'; Start-Sleep -Milliseconds 200
  Text $pw; $pw = $null; Keys '{ENTER}'
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt 45) {
    if ((Fg-Title) -eq 'Security Certificate Risk') { Cert-Dialog }
    if (Ws-LoggedOn) { return 'logged on' }
    $msg = Ui-Find (Ws-Root) 'Wrong user name or password.' $CT::Text 0.3
    if ($msg -and -not $msg.Current.IsOffscreen) { throw 'WorkStation says: Wrong user name or password.' }
    Start-Sleep -Milliseconds 500
  }
  throw "log-on did not complete; foreground: $(Fg-Title)"
}
# At log-on to localhost WorkStation shows 'Security Certificate Risk' ("The certificate presented by this server
# was issued for a different server's address"), with Trust certificate / Cancel and a box "Always trust this
# certificate". The script presses Trust certificate for this log-on only and leaves the box alone; it is the
# server on the same machine. For any other server address it does nothing and the log-on times out.
function Cert-Dialog {
  $server = try { (Ui-ById (Ws-Root) 'PART_EditableTextBox' 1).GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value } catch { '' }
  if ($server -ne 'localhost') { Start-Sleep 5; return }
  $b = Ui-Find (Fg-Root) 'Trust certificate' $CT::Button 2
  if ($b) { Ui-Invoke $b; Start-Sleep 1 }
}
# Make sure WorkStation runs and is logged on: start it if needed, then Ws-Logon.
function Ws-Ensure($user = 'admin') {
  if (-not (Ws-Proc)) {
    $ws = 'C:\Program Files (x86)\Schneider Electric EcoStruxure\Building Operation 7.1\WorkStation'
    Start-Process "$ws\SE.SBO.WorkStation.exe" -WorkingDirectory $ws
    $t = [Diagnostics.Stopwatch]::StartNew()
    while ($t.Elapsed.TotalSeconds -lt 90 -and -not (Ws-Proc)) { Start-Sleep 1 }
    if (-not (Ws-Proc)) { throw 'WorkStation did not start' }
    Start-Sleep 3
  }
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt 60 -and -not (Ws-LoggedOn) -and -not (Ui-ById (Ws-Root) 'LogOnButton' 1)) { Start-Sleep 1 }
  if (Ws-LoggedOn) { return 'already logged on' }
  Web-Back                                                   # a window kept on top would lie over the log-on form
  Ws-Logon $user
}

# System Tree item by path under the server, e.g. '/Server 1/Folder/Program'. Tree item names are '/' + object name.
function Ws-TreeItem($path) {
  $parts = $path.Trim('/').Split('/'); $node = Ui-ById (Ws-Root) 'TreeView' 5
  foreach ($n in $parts) {
    $c = New-Object System.Windows.Automation.AndCondition(
      (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::TreeItem)),
      (New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, "/$n")))
    $next = $null
    for ($i = 0; $i -lt 20 -and -not $next; $i++) {
      $next = $node.FindFirst($TS::Descendants, $c)
      if (-not $next) {
        try { $node.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand() } catch {}
        Start-Sleep -Milliseconds 300
      }
    }
    if (-not $next) { return $null }
    $node = $next
  }
  $node
}
function Ws-Select($path) {
  $t = Ws-TreeItem $path; if (-not $t) { throw "tree item $path not found" }
  try { $t.GetCurrentPattern([System.Windows.Automation.ScrollItemPattern]::Pattern).ScrollIntoView() } catch {}
  $t.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select(); Start-Sleep -Milliseconds 300
  $txt = Ui-ById $t 'objectNameTextBlock' 2; if ($txt) { Ui-Click $txt; Start-Sleep -Milliseconds 300 }   # give the tree keyboard focus
  $t
}
function Ws-Refresh($path) { [void](Ws-Select $path); Keys '{F5}'; Start-Sleep 1 }

# Create an object of a type (as named in the New Object dialog) under a parent path.
function Ws-New($parent, $typeName, $name) {
  Ws-Front; $opened = $false
  foreach ($try in 1..3) {                                   # the view of the parent may still be loading and eat the key
    [void](Ws-Select $parent); Start-Sleep -Milliseconds (400 * $try); Keys '^n'
    if (Wait-Fg '^Create New Object' 5) { $opened = $true; break }
  }
  if (-not $opened) { throw 'New Object dialog did not open' }
  $d = Fg-Root
  $f = Ui-ById $d 'FilterInfoTextBox' 5; Ui-Click $f; Text $typeName; Start-Sleep -Milliseconds 900
  $t = Ui-Find $d $typeName $CT::Text 5; if (-not $t) { Keys '{ESC}'; throw "type '$typeName' not offered here" }
  Ui-Click $t; Start-Sleep -Milliseconds 400
  $n = Ui-ById $d 'TextBox' 3; Ui-Click $n; Keys '^a'; Text $name; Start-Sleep -Milliseconds 300
  $b = Ui-Find $d 'Create' $CT::Button 3; Ui-Invoke $b
  $t0 = [Diagnostics.Stopwatch]::StartNew()
  while ($t0.Elapsed.TotalSeconds -lt 20) { if ((Fg-Title) -notmatch '^Create New Object' -and (Ws-TreeItem "$parent/$name")) { return "created $parent/$name" }; Start-Sleep -Milliseconds 400 }
  throw "object $parent/$name did not appear; foreground: $(Fg-Title)"
}

# Open a Function Block program in the classic editor (Classic Mode must be on, which WorkStation remembers).
function Fbe-Proc($name) { Get-Process $FBE -ErrorAction SilentlyContinue | ? { $_.MainWindowTitle -like "$name - *Function Block Editor" } | select -First 1 }
function Fbe-Open($path) {
  $name = $path.Trim('/').Split('/')[-1]
  if (Fbe-Proc $name) { return (Fbe-Proc $name) }
  Get-Process SE.Graphics.Editor -ErrorAction SilentlyContinue | ? { -not $_.MainWindowTitle } | Stop-Process -Force   # windowless leftover of an earlier Ctrl+E
  Ws-Front; [void](Ws-Select $path); Keys '^e'
  $t = [Diagnostics.Stopwatch]::StartNew(); $pencil = $false
  while ($t.Elapsed.TotalSeconds -lt 60) {
    $p = Fbe-Proc $name; if ($p) { Start-Sleep -Milliseconds 800; return $p }
    # With the program's tab already open, Ctrl+E can stop at the tab. The pencil left of "Show Classic Mode" starts the editor.
    if (-not $pencil -and $t.Elapsed.TotalSeconds -gt 14) {
      $c = Ui-ById (Ws-Root) 'ShowClassicMode' 3
      if ($c) { $r = $c.Current.BoundingRectangle; Ws-Front; Click ([int]($r.X - 72)) ([int]($r.Y + 11)) }
      $pencil = $true
    }
    Start-Sleep -Milliseconds 400
  }
  throw "Function Block editor did not open for $path (is Classic Mode on?)"
}
function Dialog-Button($title, $button, $sec = 4) {       # press a button in a message box, if it shows up
  $d = Top-Window $title $sec; if (-not $d) { return $false }
  $b = Ui-Find $d $button $CT::Button 2; if (-not $b) { return $false }
  Ui-Invoke $b; Start-Sleep -Milliseconds 500; return $true
}
function Fbe-Import($p, $file) {
  Menu-Do $p.MainWindowHandle 'File' 'Import*'
  FileDialog-Set 'Import' $file
  # A file not written by this editor generation gets a question box, also titled "Import", with Yes / No.
  $t = [Diagnostics.Stopwatch]::StartNew(); Start-Sleep -Milliseconds 700
  while ($t.Elapsed.TotalSeconds -lt 8) {
    Start-Sleep -Milliseconds 400
    if ((Fg-Title) -eq 'Import') {
      if (-not (Ui-ById (Fg-Root) '1148' 0.3)) { Keys 'y'; Start-Sleep -Milliseconds 800; break }   # no File name box: it is the question
    } elseif ((Fg-Title) -like '*Function Block Editor') { Start-Sleep -Milliseconds 600; if ((Fg-Title) -like '*Function Block Editor') { break } }
  }
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt 10 -and (Fg-Title) -notlike '*Function Block Editor') { Start-Sleep -Milliseconds 300 }
  if ((Fg-Title) -notlike '*Function Block Editor') { throw "after import the foreground window is '$(Fg-Title)'" }
}
function Fbe-Save($p) {
  Menu-Do $p.MainWindowHandle 'File' 'Save'
  # "Generating application..." shows while it compiles and stores; it has no title. Wait until the editor is back.
  $t = [Diagnostics.Stopwatch]::StartNew(); Start-Sleep -Milliseconds 700
  while ($t.Elapsed.TotalSeconds -lt 60 -and (Fg-Title) -notlike '*Function Block Editor') {
    if ((Fg-Title) -eq 'Tam32') {                             # the editor's own message box, e.g. "Compilation of program failed."
      $msg = ((Fg-Root).FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | % { $_.Current.Name } | ? { $_ -and $_ -ne 'OK' -and $_ -ne 'Close' }) -join ' '
      Keys '{ENTER}'; throw "editor says: $msg"
    }
    # A program of a controller that is not connected (MP-C / RP-C made offline): the progress box stays up with
    # "Save successful. Downloading to device... Download failed, device is offline." and an Ok button (only the
    # last line is readable from outside). Saved is saved.
    if ($t.Elapsed.TotalSeconds -gt 4 -and -not (Fg-Title)) {
      $txt = ((Fg-Root).FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | % { $_.Current.Name }) -join ' '
      if ($txt -match 'device is offline') {
        Keys '{ENTER}'; Log 'saved to the server; not downloaded, the device is offline'
        $w = [Diagnostics.Stopwatch]::StartNew()                 # the box takes a moment to go; then the editor is in front again
        while ($w.Elapsed.TotalSeconds -lt 8 -and (Fg-Title) -notlike '*Function Block Editor') { Start-Sleep -Milliseconds 400; if (-not (Fg-Title)) { Keys '{ENTER}' } }
        if ((Fg-Title) -notlike '*Function Block Editor') { [void][W32]::SetForegroundWindow($p.MainWindowHandle); Start-Sleep 1 }
        return
      }
      if ($txt -match 'failed' -and $txt -notmatch 'Download failed') { Keys '{ENTER}'; throw "editor says: $txt" }
    }
    Start-Sleep -Milliseconds 300
  }
  if ((Fg-Title) -notlike '*Function Block Editor') { throw "after Save the foreground window is '$(Fg-Title)'" }
  Start-Sleep -Milliseconds 500
}
function Fbe-Exit($p) {
  Menu-Do $p.MainWindowHandle 'File' 'Exit'
  if (-not $p.WaitForExit(20000)) { throw "editor still open; foreground: $(Fg-Title)" }
}

# The whole chain: make the program if it is not there, import the text file, save (compiles), exit.
# Compiler messages for a program file, without the server: the editor started alone opens the file and runs
# Options > Simulate, which compiles and names the fault ("Public constant used more than once: X"), where a save
# to the server only says "Compilation of program failed". One message per run. Returns 'compiles' when none came.
function Fb-Check($file) {
  if (-not (Test-Path $file)) { throw "no file $file" }
  Get-Process $FBE -ea 0 | ? { $_.MainWindowTitle -like '*Menta Editor*' } | Stop-Process -Force
  $ws = 'C:\Program Files (x86)\Schneider Electric EcoStruxure\Building Operation 7.1\WorkStation'
  $p = Start-Process "$ws\$FBE.exe" -WorkingDirectory $ws -PassThru
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt 30) { Start-Sleep 1; $p.Refresh(); if ($p.MainWindowTitle -like '*Menta Editor*') { break } }
  if ($p.MainWindowTitle -notlike '*Menta Editor*') { throw 'the editor did not start alone' }
  $res = 'compiles'
  try {
    Activate 'Menta Editor' | Out-Null; Menu-Do $p.MainWindowHandle 'File' 'Open*'
    if (-not (Wait-Fg '^Open' 8)) { throw "Open dialog did not show; foreground: $(Fg-Title)" }
    FileDialog-Set 'Open' $file; Start-Sleep 3
    if ((Fg-Title) -notlike '*Menta Editor*') { Keys 'y'; Start-Sleep 3 }        # "not a ... program, continue?"
    Menu-Do $p.MainWindowHandle 'Options' 'Simulate'
    $t = [Diagnostics.Stopwatch]::StartNew()
    while ($t.Elapsed.TotalSeconds -lt 15) {
      Start-Sleep -Milliseconds 500
      if ((Fg-Title) -eq 'tam32') {
        $res = ((Fg-Root).FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | % { $_.Current.Name } | ? { $_ -and $_ -ne 'OK' -and $_ -ne 'Close' }) -join ' '
        Keys '{ENTER}'; break
      }
    }
  } finally { Start-Sleep 1; Get-Process $FBE -ea 0 | ? { $_.Id -eq $p.Id } | Stop-Process -Force }
  $res
}

# $type: 'Function Block Program' on a server; 'SpaceLogic Function Block Program' in the Application of an MP-C / RP-C.
function Fb-Load($parent, $name, $file, $type = 'Function Block Program') {
  $sw = [Diagnostics.Stopwatch]::StartNew(); Ws-Front
  # An editor left over from an earlier, failed load of a program with this name belongs to another (perhaps
  # deleted) object; Fbe-Open would take it for the right one, and a save from it ends with "Failed to parse
  # Menta application". So no editor with this name may be open at the start, and none is left behind on a failure.
  Get-Process $FBE -ErrorAction SilentlyContinue | ? { $_.MainWindowTitle -like "$name - *Function Block Editor" } | Stop-Process -Force
  Start-Sleep -Milliseconds 500
  if (-not (Ws-TreeItem "$parent/$name")) { Log (Ws-New $parent $type $name) }
  $p = Fbe-Open "$parent/$name"; Log "editor open $([int]$sw.Elapsed.TotalSeconds) s"
  try {
    Fbe-Import $p $file; Log "imported $([int]$sw.Elapsed.TotalSeconds) s"
    Start-Sleep ([int][Math]::Min(15, 2 + (Get-Item $file).Length / 12000))     # let a large import settle before the save
    Fbe-Save $p; Log "saved $([int]$sw.Elapsed.TotalSeconds) s"
    Fbe-Exit $p; Log "editor closed $([int]$sw.Elapsed.TotalSeconds) s"
  } catch {
    Get-Process $FBE -ErrorAction SilentlyContinue | ? { $_.Id -eq $p.Id } | Stop-Process -Force
    throw
  }
}

# Export an object to an xml file (overwrites).
# $mode: Standard (bindings inside the exported set), Special (every binding, also to objects outside it: the
# one to use for reading bindings back) or Library (inside only, for re-use elsewhere).
function Ws-Export($path, $file, $mode = 'Standard') {
  Remove-Item $file -ErrorAction SilentlyContinue
  Ws-Front; $t = Ws-Select $path; $txt = Ui-ById $t 'objectNameTextBlock' 2
  Ui-Click $txt -Right; Start-Sleep -Milliseconds 800
  $m = Ui-Find $A::RootElement 'Export...' $CT::MenuItem 5; if (-not $m) { Keys '{ESC}'; throw 'Export... not in the context menu' }
  Ui-Invoke $m
  if (-not (Wait-Fg '^Export preview' 10)) { throw 'Export preview did not open' }
  $rb = @{ Standard = 'rbDefault'; Special = 'rbSpecial'; Library = 'rbLibrary' }[$mode]; if (-not $rb) { throw "export mode $mode ?" }
  $r = Ui-ById (Fg-Root) $rb 5; if (-not $r) { throw "export preview: no $rb" }
  $r.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select(); Start-Sleep -Milliseconds 300
  Ui-Invoke (Ui-ById (Fg-Root) 'btnExport' 3)
  if (-not (Wait-Fg '^Save As' 10)) { throw 'Save As did not open' }
  Text $file; Keys '{ENTER}'
  $t0 = [Diagnostics.Stopwatch]::StartNew()
  while ($t0.Elapsed.TotalSeconds -lt 30 -and -not (Test-Path $file)) { Start-Sleep -Milliseconds 300 }
  Start-Sleep 1; if ((Fg-Title) -match '^Export') { Keys '{ENTER}' }
  if (-not (Test-Path $file)) { throw "export file not written; foreground: $(Fg-Title)" }
  "exported $path -> $file ($((Get-Item $file).Length) bytes)"
}

# Import an export file (.xml) below $parent: File > Import..., file dialog, preview, Import, Close. The preview
# counts errors; with any error nothing is imported and the first lines of the dialog are thrown.
function Ws-Import($parent, $file) {
  if (-not (Test-Path $file)) { throw "no file $file" }
  Ws-Front; [void](Ws-Select $parent)
  Ui-Click (Ui-Find (Ws-Root) 'File' $CT::MenuItem 5); Start-Sleep -Milliseconds 800
  $m = Ui-Find $A::RootElement 'Import...' $CT::MenuItem 5; if (-not $m) { Keys '{ESC}'; throw 'Import... not in the File menu' }
  Ui-Invoke $m
  if (-not (Wait-Fg '^Open' 10)) { throw 'file dialog did not open' }
  Keys '%n'; Start-Sleep -Milliseconds 400; Text $file; Keys '{ENTER}'
  if (-not (Wait-Fg '^Import' 20)) { throw "import preview did not open; foreground: $(Fg-Title)" }
  $b = Ui-ById (Fg-Root) 'buttonImport' 30; if (-not $b) { throw 'import preview: no Import button' }
  $txt = (Ui-Find (Fg-Root) '' $CT::Text 2 -All) | % { $_.Current.Name }
  $err = $txt | ? { $_ -match '^\d+ error' } | select -First 1
  if ($err -and $err -notmatch '^0 ') {
    Ui-Invoke (Ui-ById (Fg-Root) 'ErrorsButton' 2); Start-Sleep 1
    $msg = ((Ui-Find (Fg-Root) '' $CT::Text 2 -All) | % { $_.Current.Name } | ? { $_ -and $_.Length -gt 25 } | select -First 6) -join ' | '
    Ui-Invoke (Ui-ById (Fg-Root) 'buttonCancel' 3); throw "import refused: $err : $msg"
  }
  Ui-Invoke $b
  $t0 = [Diagnostics.Stopwatch]::StartNew(); $c = $null
  while ($t0.Elapsed.TotalSeconds -lt 120 -and -not $c) { Start-Sleep 1; $c = Ui-ById (Fg-Root) 'btnClose' 1 }
  if (-not $c) { throw "import did not finish; foreground: $(Fg-Title)" }
  $done = [bool]((Ui-Find (Fg-Root) '' $CT::Text 2 -All) | ? { $_.Current.Name -like 'Finished Importing*' })
  $all = ((Ui-Find (Fg-Root) '' $CT::Text 2 -All) | % { $_.Current.Name } | ? { $_ }) -join ' | '
  Ui-Invoke $c; Start-Sleep 1
  if (-not $done) { throw "import: $all" }
  "imported $file below $parent"
}

# Delete an object. WorkStation asks for confirmation in a dialog titled "Confirm Delete".
function Ws-Delete($path) {
  # a path that ends in a slash (an empty variable at its end) would name the parent: seen deleting a whole MQTT client
  if ($path -match '/\s*$' -or $path -notmatch '^/[^/]+/[^/]') { throw "Ws-Delete: refusing path '$path'" }
  Ws-Front; if (-not (Ws-TreeItem $path)) { return "not there: $path" }
  $t = ''
  foreach ($try in 1..3) {                                   # right after another delete the tree is still refreshing
    Start-Sleep -Milliseconds (500 * $try); [void](Ws-Select $path); Start-Sleep -Milliseconds 400
    # While the tree is still refreshing after an earlier delete, the click of Ws-Select can land on another row
    # (seen: the parent, which DEL then removed). Press DEL only when the wanted item is the selected one.
    $it = Ws-TreeItem $path
    if (-not $it -or -not $it.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Current.IsSelected) { Start-Sleep 2; continue }
    Keys '{DEL}'; Start-Sleep -Milliseconds 1200
    $t = Fg-Title
    if ($t -notlike '*WorkStation (7*') { $y = Ui-Find (Fg-Root) 'Yes' $CT::Button 2; if ($y) { Ui-Invoke $y } else { Keys '{ENTER}' } }
    $t0 = [Diagnostics.Stopwatch]::StartNew()
    while ($t0.Elapsed.TotalSeconds -lt 10 -and (Ws-TreeItem $path)) { Start-Sleep -Milliseconds 500 }
    if (-not (Ws-TreeItem $path)) { return "deleted $path" }
  }
  throw "still there: $path (dialog was '$t', foreground now '$(Fg-Title)')"
}

# ---- tabs, opening, bindings, graphics -------------------------------------------------------------------------
# Close a work area tab by its title, e.g. 'Bindings: DH-ex2'. The x sits 13 px right of the title text.
function Tab-Close($title) {
  $t = Ui-Find (Ws-Root) $title $CT::Text 2; if (-not $t) { return $false }
  $r = $t.Current.BoundingRectangle; Click ([int]($r.X + $r.Width + 13)) ([int]($r.Y + $r.Height / 2)); Start-Sleep -Milliseconds 900
  if ((Fg-Title) -notlike '*WorkStation (7*') { Keys 'n'; Start-Sleep -Milliseconds 600 }      # "save changes?" -> No
  return $true
}
# Open an object in its default view (graphic viewer, program variables ...): double-click in the System Tree.
function Ws-Open($path) {
  Ws-Front; $t = Ws-Select $path; $txt = Ui-ById $t 'objectNameTextBlock' 2; $x, $y = Ui-Center $txt
  Click $x $y; Start-Sleep -Milliseconds 80; Click $x $y; Start-Sleep 2
}

# Bind binding points of an object. $pairs: ordered list of @(point name, path) with paths as typed in the
# Bindings view: absolute ('/Server 1/Prog/MODULE/Signal') or relative. Saves and closes the Bindings tab.
function Ws-Bind($path, $pairs) {
  $name = $path.Trim('/').Split('/')[-1]
  Ws-Front; [void](Ws-Select $path); Keys '^b'
  $r = Ws-Root; $list = Ui-ById $r 'bindingList' 15       # a program with many signals needs well over 5 s
  if (-not $list) { Ws-Front; [void](Ws-Select $path); Start-Sleep 1; Keys '^b'; $list = Ui-ById $r 'bindingList' 25 }
  if (-not $list) { throw "Bindings view did not open for $path" }
  $tabTitle = Ui-Find $r "Bindings: $name" $CT::Text 5; if (-not $tabTitle) { throw "Bindings tab of $name not found" }
  $filters = @(); foreach ($e in (Ui-Find $r $null $CT::Edit 3 -All)) { if ($e.Current.AutomationId -eq 'FilterInfoTextBox') { $filters += $e } }
  $filter = $filters | select -First 1
  $done = 0; $missing = @()
  foreach ($p in $pairs) {
    $point, $target = $p[0], $p[1]
    Ui-Click $filter; Keys '^a'; Text $point; Start-Sleep -Milliseconds 700
    $hit = $null
    foreach ($it in (Ui-Find $list $null $CT::DataItem 3 -All)) {
      $n = Ui-ById $it 'DisplayName' 0.2
      if ($n -and $n.Current.Name -eq $point) { $hit = $it; break }
    }
    if (-not $hit) { $missing += $point; continue }
    $e = Ui-ById $hit 'PART_tbPathText' 1; if (-not $e) { $missing += $point; continue }
    Ui-Click $e; Start-Sleep -Milliseconds 200; Keys '^a'; Text $target; Keys '{ENTER}'; Start-Sleep -Milliseconds 400
    # Save before the filter changes again: an entry that is still pending is dropped when the list is refiltered.
    $s = Ui-ById $r 'ButtonSave' 3; Ui-Invoke $s; Start-Sleep -Milliseconds 1300; $done++
    if ((Fg-Title) -notlike '*WorkStation (7*') { $t = Fg-Title; Keys '{ESC}'; throw "saving the binding of ${point}: foreground window '$t'" }
  }
  Ui-Click $filter; Keys '^a'; Keys '{DEL}'; Start-Sleep -Milliseconds 300
  if ((Fg-Title) -notlike '*WorkStation (7*') { $t = Fg-Title; Keys '{ESC}'; throw "after saving bindings the foreground window is '$t'" }
  foreach ($try in 1..3) { [void](Tab-Close "Bindings: $name"); Start-Sleep -Milliseconds 500; if (-not (Ui-Find (Ws-Root) "Bindings: $name" $CT::Text 0.5)) { break } }
  if ($missing) { throw "bound $done, binding points not found: $($missing -join ', ')" }
  "bound $done points of $path"
}

# Graphics Editor (SE.Graphics.Editor.exe, WinForms; its toolbar is not reachable by name, so the File menu is
# opened by position inside the editor window: File at +36,+44, Import... at +72,+154).
function Gfx-Proc($name) { Find-Window "Graphic: $name - " 'SE.Graphics.Editor' }
function Gfx-Load($parent, $name, $file) {
  $sw = [Diagnostics.Stopwatch]::StartNew(); Ws-Front
  if (-not (Ws-TreeItem "$parent/$name")) { Log (Ws-New $parent 'Graphic' $name) }
  [void](Ws-Select "$parent/$name"); Keys '^e'
  $t = [Diagnostics.Stopwatch]::StartNew(); $w = $null
  while ($t.Elapsed.TotalSeconds -lt 60 -and -not $w) { $w = Gfx-Proc $name; Start-Sleep -Milliseconds 500 }
  if (-not $w) { throw "Graphics Editor did not open for $parent/$name" }
  Start-Sleep 3; Log "graphics editor open $([int]$sw.Elapsed.TotalSeconds) s"
  if (-not (Activate "Graphic: $name - " 'SE.Graphics.Editor')) { throw 'Graphics Editor not brought to front' }
  $b = (Ui-Root $w.MainWindowHandle).Current.BoundingRectangle
  # Replace the whole document through the Source view (toolbar: Design at +370,+44, Source at +433,+44).
  # File > Import... (+36,+44 then +72,+154) also reads a .tgml, but it adds the content as a new layer and
  # keeps the page size of the empty graphic, so a larger drawing is cropped.
  $doc = (Get-Content $file -Raw -Encoding UTF8) -replace '(?s)^.*?(<Tgml )', '$1'
  Set-Clipboard -Value $doc
  Click ([int]$b.X + 433) ([int]$b.Y + 44); Start-Sleep 3
  Click ([int]$b.X + 520) ([int]$b.Y + 300); Start-Sleep -Milliseconds 400; Keys '^a'; Start-Sleep -Milliseconds 300; Keys '^v'; Start-Sleep 2
  Click ([int]$b.X + 370) ([int]$b.Y + 44); Start-Sleep 4
  if ((Fg-Title) -notlike "Graphic: $name*") { throw "after loading the source the foreground window is '$(Fg-Title)'" }
  Log "source loaded $([int]$sw.Elapsed.TotalSeconds) s"
  Keys '^s'; Start-Sleep 4
  if ((Fg-Title) -notlike "Graphic: $name*") { throw "after save the foreground window is '$(Fg-Title)'" }
  Keys '%{F4}'
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt 30 -and (Gfx-Proc $name)) {
    if ((Fg-Title) -notlike "Graphic: $name*" -and (Fg-Title) -notlike '*WorkStation (7*' -and (Fg-Title)) { Keys 'y' }   # save changes? -> Yes
    Start-Sleep -Milliseconds 500
  }
  if (Gfx-Proc $name) { throw "Graphics Editor still open; foreground: $(Fg-Title)" }
  Log "graphics editor closed $([int]$sw.Elapsed.TotalSeconds) s"
}

# ---- property pages, MQTT (IoT Interface > MQTT client > Data Group) --------------------------------------------
# Labels of a property page are not exposed to UI Automation, so fields are taken by kind and order (seen 2026-11-21).
function Prop-Grid {
  $g = Ui-ById (Ws-Root) 'PropertyGridContainer' 5; if ($g) { return $g }
  # A page that opened into a fresh work area tab is drawn but not exposed to UI Automation. Going to another
  # object and back in the same tab exposes it (seen 2026-11-21), so do that with the System Tree selection.
  $ti = New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::TreeItem)
  foreach ($try in 1..3) {
    $items = @((Ws-Root).FindAll($TS::Descendants, $ti))
    $sel = $items | ? { try { $_.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Current.IsSelected } catch { $false } } | select -First 1
    if ($sel -and $items.Count -gt 1 -and $sel -ne $items[0]) {
      Ws-Front; Ui-Click (Ui-ById $items[0] 'objectNameTextBlock' 2); Start-Sleep -Milliseconds (1500 * $try)
      Ui-Click (Ui-ById $sel 'objectNameTextBlock' 2); Start-Sleep -Milliseconds (2000 * $try)
    }
    $g = Ui-ById (Ws-Root) 'PropertyGridContainer' 6; if ($g) { return $g }
  }
  throw 'no property page on screen'
}
function Prop-All($type, $aid) {
  $c = New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $type)
  @((Prop-Grid).FindAll($TS::Descendants, $c) | ? { -not $_.Current.BoundingRectangle.IsEmpty -and (-not $aid -or $_.Current.AutomationId -eq $aid) })
}
function Prop-Combo($i, $letter) { Ui-Click (Prop-All $CT::ComboBox)[$i]; Start-Sleep -Milliseconds 500; Keys $letter; Keys '{ENTER}'; Start-Sleep -Milliseconds 400 }
function Prop-Paste($el, $text) { Ui-Click $el; Start-Sleep -Milliseconds 300; Keys '^a'; Set-Clipboard $text; Keys '^v'; Start-Sleep -Milliseconds 300; Keys '{TAB}'; Start-Sleep -Milliseconds 300 }
function Prop-Tab($name) { Ui-Click (Ui-Find (Prop-Grid) $name $CT::Text 5); Start-Sleep -Milliseconds 1500 }
function Ws-Save { Ui-Invoke (Ui-ById (Ws-Root) 'ButtonSave' 3); Start-Sleep 3; if ((Fg-Title) -notlike '*WorkStation (7*') { throw "save raised: $(Fg-Title)" } }

# MQTT client under an IoT Interface: plain MQTT to $broker port 1883, no TLS, payload $format, enabled.
# Nothing is published while the value format is empty.
function Mq-Client($parent, $name, $broker = '127.0.0.1', $format = '@(Value)') {
  if (-not (Ws-TreeItem "$parent/$name")) { Log (Ws-New $parent 'MQTT client' $name) }; [void](Ws-Select "$parent/$name"); Start-Sleep 2
  Ui-Click (Ui-Find (Ws-Root) 'Properties' $CT::TabItem 5); Start-Sleep 2
  Prop-Paste (Prop-All $CT::Edit 'EditField')[3] $format                 # Basic: message start, end, delimiter, value format
  Prop-Tab 'Connection'
  Prop-Paste (Prop-All $CT::Edit 'TextBox')[2] $broker                   # client id, user name, host, ports ...
  Prop-Combo 3 'N'                                                       # enabled, protocol, status, enable TLS
  Prop-Combo 0 'Y'
  Ws-Save; "MQTT client $parent/$name -> $broker"
}
# One row of an open "Select Object and Property" dialog: tree path under the server, then the property.
# Rows have no names either; the Path box tells which row a click landed on.
function Dp-Pick($parts, $prop) {
  $d = Fg-Root; $n = $d
  $first = New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, "/$($parts[0])")), (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::TreeItem)))
  $t = [Diagnostics.Stopwatch]::StartNew()                    # the tree fills in a second or two after the dialog shows
  while ($t.Elapsed.TotalSeconds -lt 10 -and -not $d.FindFirst($TS::Descendants, $first)) { Start-Sleep -Milliseconds 300 }
  foreach ($p in $parts) {
    $c = New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, "/$p")), (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::TreeItem)))
    $n = $n.FindFirst($TS::Descendants, $c); if (-not $n) { Keys '{ESC}'; throw "no tree item $p" }
    try { $n.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand() } catch {}; Start-Sleep -Milliseconds 900
  }
  Ui-Click (Ui-ById $n 'objectNameTextBlock' 2); Start-Sleep -Milliseconds 1500
  $vp = $d.FindFirst($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::Edit))).GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
  foreach ($r in $d.FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::DataItem)))) {
    $b = $r.Current.BoundingRectangle; if ($b.IsEmpty) { continue }
    Click ([int]($b.X + 200)) ([int]($b.Y + $b.Height / 2)); Start-Sleep -Milliseconds 150
    if (($vp.Current.Value -replace '.*/', '') -eq $prop) { Ui-Invoke (Ui-Find $d 'Select' $CT::Button 3); Start-Sleep -Milliseconds 800; return "$($parts -join '/')/$prop" }
  }
  Keys '{ESC}'; throw "property $prop not found under $($parts -join '/')"
}
# Data Group under an MQTT client: event driven plus every $seconds, publishing $points = @(@(@('Prog','MODULE'),'Signal'), ...).
# Topic of each point is its EBO path ("Server 1/Prog/MODULE/Signal").
function Mq-Group($client, $name, $points, $seconds = 10) {
  if (-not (Ws-TreeItem "$client/$name")) { Log (Ws-New $client 'Data Group' $name) }; [void](Ws-Select "$client/$name"); Start-Sleep 3
  Prop-Combo 2 'Y'                                                       # QoS, retain, event driven, ..., [6] enable interval
  Prop-Combo 6 'Y'
  $x, $y = Ui-Center (Prop-All $CT::ComboBox)[6]                         # interval: minutes then seconds, one row below
  Click ($x + 44) ($y + 39); Start-Sleep -Milliseconds 300; Keys '^a'; Text '0'; Keys '{TAB}'; Start-Sleep -Milliseconds 300; Keys '^a'; Text "$seconds"; Keys '{TAB}'
  Mq-Points $points
  Ws-Save; "data group $client/${name}: $(@(Mq-Listed).Count) points"
}
# Add data points to the data group whose property page is on screen ("+" of Data points = automation id AddButton).
function Mq-Points($points) {
  foreach ($p in $points) {
    $add = Ui-ById (Prop-Grid) 'AddButton' 5; if (-not $add) { throw 'no Data points add button on this page' }
    Ws-Front; Ui-Click $add; if (-not (Wait-Fg '^Select Object' 8)) { throw 'data point picker did not open' }
    Log ('data point ' + (Dp-Pick $p[0] $p[1]))
  }
}
# Paths in the Data points list of the page on screen, as shown ("../../../Prog/MODULE/Signal").
function Mq-Listed {
  $l = Ui-ById (Prop-Grid) 'ListViewControl' 3; if (-not $l) { return @() }
  @($l.FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::Text))) | % { $_.Current.Name } | ? { $_ -match '/' })
}
# Close WorkStation and leave the bare desktop (for a run that starts from nothing).
function Ws-Close {
  $p = Ws-Proc; if ($p) { $p = Get-Process -Id $p.Id; [void]$p.CloseMainWindow(); Start-Sleep 4; if ((Fg-Title) -notlike '*WorkStation (7*' -and (Fg-Title)) { Keys '{ENTER}' }
    if (-not $p.WaitForExit(8000)) { Stop-Process -Id $p.Id -Force } }
  (New-Object -ComObject Shell.Application).MinimizeAll(); Start-Sleep 1; 'desktop'
}
# Stopwatch over the taskbar clock (timer.ps1): Timer-Start [seconds already run], Timer-Stop freezes the reading,
# Timer-Close removes it.
function Timer-Close { Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | ? { $_.CommandLine -like '*timer.ps1*' } | % { Stop-Process -Id $_.ProcessId -Force }; Remove-Item C:\agentwork\ebo\timer.stop -ErrorAction SilentlyContinue }
function Timer-Start($offset = 0) { Timer-Close; Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\agentwork\ebo\timer.ps1','-Offset',"$offset" }
function Timer-Stop { 'stop' | Set-Content C:\agentwork\ebo\timer.stop }
# A web page in its own Edge window (no tabs, no address bar), kept above the other windows at x, y, w, h.
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class W32Top { [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags); }
"@
function Web-Top($url, $title, $x, $y, $w, $h) {
  $p = Get-Process msedge -ea 0 | ? { $_.MainWindowTitle -like "*$title*" } | select -First 1
  if (-not $p) {
    Start-Process 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' -ArgumentList "--app=$url", '--no-first-run', "--window-size=$w,$h", "--window-position=$x,$y"
    $t = [Diagnostics.Stopwatch]::StartNew()
    while ($t.Elapsed.TotalSeconds -lt 30 -and -not $p) { Start-Sleep 1; $p = Get-Process msedge -ea 0 | ? { $_.MainWindowTitle -like "*$title*" } | select -First 1 }
    if (-not $p) { throw "no window titled $title" }
  }
  if ([W32]::IsIconic($p.MainWindowHandle)) { [void][W32]::ShowWindow($p.MainWindowHandle, 9) }
  [void][W32Top]::SetWindowPos($p.MainWindowHandle, [IntPtr](-1), $x, $y, $w, $h, 0x0010); "window '$title' on top"
}
# Take web windows out of the way (not on top any more, minimised). Ws-Ensure does this before a log-on; call Web-Top again afterwards.
# WebStation in an Edge window of its own. $path: object to show, e.g. '/Server 1/Folder/Dashboard'.
# The server's certificate is its own, made for another name: for https://localhost only, the warning page is
# passed (Advanced, Continue). No other address is ever passed.
function Web-Station($path = '', $x = 0, $y = 0, $w = 1600, $h = 1150) {
  $url = 'https://localhost/' + $(if ($path) { '#' + (($path -split '/' | % { [uri]::EscapeDataString($_) }) -join '/') } else { '' })
  Get-Process msedge -ea 0 | ? { $_.MainWindowTitle -match 'Building Operation|Privacy error' } | % { [void]$_.CloseMainWindow() }; Start-Sleep 1
  Start-Process 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' -ArgumentList "--app=$url", '--no-first-run', "--window-size=$w,$h", "--window-position=$x,$y"
  $t = [Diagnostics.Stopwatch]::StartNew(); $p = $null
  while ($t.Elapsed.TotalSeconds -lt 40) {
    Start-Sleep 1
    $p = Get-Process msedge -ea 0 | ? { $_.MainWindowTitle -match 'Building Operation|Privacy error' } | select -First 1
    if ($p -and $p.MainWindowTitle -match 'Privacy error') {
      $r = Ui-Root $p.MainWindowHandle
      $adv = Ui-Find $r 'Advanced' $CT::Button 3; if ($adv) { Ui-Invoke $adv; Start-Sleep 1 }
      $go = Ui-Find $r 'Continue to localhost (unsafe)' $CT::Hyperlink 3; if ($go) { Ui-Invoke $go }
      Start-Sleep 3
    } elseif ($p) { break }
  }
  if (-not $p) { throw 'WebStation window did not open' }
  [void][W32Top]::SetWindowPos($p.MainWindowHandle, [IntPtr](-1), $x, $y, $w, $h, 0x0010)
  "WebStation window open: $($p.MainWindowTitle)"
}
function Web-Proc { Get-Process msedge -ea 0 | ? { $_.MainWindowTitle -match 'Building Operation' } | select -First 1 }
# Log on at the WebStation form. Password from C:\agentwork\ebo\.pw (written by `ebo.sh weblogon` from the vault),
# set straight into the field, never typed or echoed; the file is removed at once.
function Web-Logon($user = 'admin') {
  if (-not (Web-Proc)) { [void](Web-Station) }
  $r = Ui-Root (Web-Proc).MainWindowHandle
  $pwBox = Ui-ById $r 'txtPassWord' 15; if (-not $pwBox) { return 'no log-on form: already logged on' }
  $f = 'C:\agentwork\ebo\.pw'; if (-not (Test-Path $f)) { throw 'no password file' }
  $pw = [IO.File]::ReadAllText($f); Remove-Item $f -Force
  Ui-SetValue (Ui-ById $r 'txtUserID' 3) $user; Ui-SetValue $pwBox $pw; $pw = $null
  Ui-Invoke (Ui-ById $r 'login' 3)
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt 40) {
    Start-Sleep 1
    if (-not (Ui-ById $r 'txtPassWord' 0.5)) {
      # Edge offers to keep the password: always refused
      $no = Ui-Find $A::RootElement 'Not now' $CT::Button 6; if ($no) { Ui-Invoke $no }
      return 'logged on to WebStation'
    }
  }
  throw 'WebStation log-on did not complete'
}
function Web-Back {
  Get-Process msedge -ea 0 | ? { $_.MainWindowHandle -ne 0 } | % { [void][W32Top]::SetWindowPos($_.MainWindowHandle, [IntPtr](-2), 0, 0, 0, 0, 0x0013); [void][W32]::ShowWindow($_.MainWindowHandle, 6) }
}
