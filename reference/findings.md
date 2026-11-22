# EBO WorkStation by script: findings

Notes taken while getting Schneider EcoStruxure Building Operation to accept programs without hand clicking.
Each fact carries the date it was seen, on EBO 7.1.1.132. Nothing here comes from Schneider documentation of an
interface: it is what the WorkStation user interface did when driven from outside, so expect differences on other
versions.

## The machine

- A Windows machine with EBO 7.1.1 installed and a valid licence: Enterprise Server (service
  `Building Operation 7.1 Enterprise Server`, ports 80 / 443 / 4444) and WorkStation, both on that machine. No
  automation server hardware: programs are created directly under `/Server 1`.
- The driver runs on the same machine, in your own desktop session, and works WorkStation's windows: it takes the
  keyboard and the mouse while a command runs. Hands off until it is done.
- Program files: `C:\Program Files (x86)\Schneider Electric EcoStruxure\Building Operation 7.1\`.
  Data: `C:\ProgramData\Schneider Electric EcoStruxure\Building Operation 7.1\`.
- **Block catalogue**: `scripts/aut.py` checks block names and parameter counts against the editor's own catalogue,
  which is Schneider's file and not part of this skill. Copy it once from your installation into `reference/`:
  `...\Building Operation 7.1\WorkStation\MentaBlocks.xml`
- A test installation, not a production server: the driver creates and deletes objects under `/Server 1` and
  types into whatever window is in front.

## Ways in

| Lane | How | Use for |
|---|---|---|
| Plain PowerShell | `scripts/ebo.sh sys '<powershell>'` | files, services, reading exports |
| Screen | `scripts/ebo.sh shot <png>` | seeing the desktop |
| EBO driver | `scripts/ebo.sh run '<powershell>'`: PowerShell with `win/lib.ps1` and `win/ebo.ps1` loaded | everything in WorkStation and the editor: by UI Automation names and menu command ids |

- Screen: the driver finds WorkStation's elements by name and clicks where they are, so no fixed screen size is
  needed. A few clicks are placed a fixed number of pixels from an element or a window corner (graphics editor
  menu, the pencil beside "Show Classic Mode", some property fields); those offsets were measured at 100 %
  display scaling. Everything here was worked out at 1600x1200, 100 %. 1024x768 is too small for the editor.
  Other sizes and other scaling are not tested: if a click lands beside its target, take a screenshot and look.
- `Show Classic Mode` switched on once in WorkStation (it stays on across log-ons).
- Working folder: `C:\agentwork\ebo` (`ebo.sh setup` makes it; `ebo.sh put` copies a file there).

## What does not work

- **WorkStation automation API** (`SE.WorkStation.Automation.Interface.dll`,
  `AutomationClient(licenseKey)`, interfaces `IProgram`, `IScript`, `IAdvanced`, `IInterchange` ...):
  `Open` returns `Failed to open AutomationServer. License was not found.` with an empty key. It needs an SDK
  licence key. Not to be worked around. With a key, this API would replace the whole GUI lane (program text in
  and out as strings).

## Server log-on

- WorkStation log-on: user `admin`, server `localhost`. **`scripts/ebo.sh logon`** does it: starts
  WorkStation if it is not running, types user and password, and answers the certificate question. The password
  is typed by the user into a Windows credential box that `ebo.sh logon` opens (or comes from
  `EBO_ADMIN_PASSWORD` in the environment of one child process, see the head of `ebo.sh`) and goes
  into `C:\agentwork\ebo\.pw`, which `Ws-Logon` reads and deletes; it is never printed and never on a command
  line. Safe to call when already logged on. Logging on by hand works just as well.
- Log-on to `localhost` raises `Security Certificate Risk` ("issued for a different server's address"). The
  script presses `Trust certificate` for that log-on only, never ticks "Always trust this certificate", and
  does nothing for any other server address. Unanswered, the log-on ends with "Logon has timed out".
- Log off: `Shift+F4`.

## WorkStation by keyboard and mouse (1600x1200 coordinates unless said)

- New object: select the parent in the System Tree, `Ctrl+N`, type into the quick filter
  (`Function Block` leaves `Program > Function Block Program`), click the type, fill Name, Create.
- Export: right-click the object, `Export...`, dialog `Export preview` (binding mode `Export`),
  button Export, `Save As` dialog takes a typed full path and Enter, then `Close`.
- `File > Import...` exists (not yet used).
- **Context menus open up or down depending on room**, so menu item coordinates from one
  resolution or tree position are wrong at another. Screenshot the open menu before clicking in it,
  and check `fg` after each step: typed text that lands in the wrong window is the risk.
- Dialog chain of an export answers to the keyboard: `Export preview` Enter, `Save As` typed
  path + Enter, `Export` (result) Enter.
- Open a program for editing: select it, `Ctrl+E`. 7.1 opens the new embedded editor (block
  library on the left, canvas, Variables / Constants / Bindings / Validation / Simulation tabs).
  The `Show Classic Mode` switch (top right, 1411,212) shows the Variables view and a pencil
  button (1317,212) that starts the classic editor (`tam32.exe`, window
  `<name> - Building Operation Function Block Editor`, about 12 s to appear).

## Classic Function Block editor: program text in from a file (works, 2026-11-21)

- Menu `File`: Save, Import..., Export..., Print, Exit. `Alt+F` opened the Import dialog directly
  on one occasion; click the menu and screenshot rather than trust the accelerator.
- `File > Import...` takes `*.aut;*.mta`: type the full path in File name, Enter. A file not saved
  by this EBO generation gets the question "The selected program is not a StruxureWare Menta
  Program ... Do you want to continue?" Answer `y`.
- `File > Save` writes to the server and compiles. After `File > Exit` the WorkStation Variables
  view lists the program's modules and `Compilation valid` reads True.
- Proven with the sample program `STR350Config_C.AUT` that ships in the WorkStation folder.
- A Function Block program object is made in WorkStation (it owns task, bindings, values); its
  logic is the diagram held by this editor. What was seen:
  the imported diagram became the program's own content and compiled.

## First program of our own, end to end (2026-11-21)

`examples/blink.aut`, written by hand, loaded into `/Server 1/FB_Blink`:

1. WorkStation: select `Server 1`, `Ctrl+N`, filter `Function Block`, pick
   `Function Block Program`, name, Create.
2. Select the program in the tree, `Ctrl+E` (same as right-click > Edit). With Classic Mode left
   on from before, this goes straight to the classic editor.
3. Editor: `File > Import...`, path of the `.aut`, Enter, `y`. The diagram draws itself.
4. `File > Save`, `File > Exit`.
5. WorkStation, program tab: `F5`. `Compilation valid` True, `Status` Running, `Number of cycles`
   counting. Expand the program row, then `Outputs`: public outputs with live values.

Result: `Above20Out` True (PVR 21.5 through HYST 20/19), `BlinkOut` alternating True / False
between screenshots one second apart (OSC cycle 4 s, pulse 2 s). So the Enterprise Server runs
Function Block programs itself and the Variables view is the read-back.

What the hand-written file needed, and no more:

```
[Aut]
#1,8,7
{41,27
#1 "Blink" [8,6,0,0] '','' = OSC (4,2)
#2 "BlinkOut" [34,6,0,0] '','' = BO ()
#3 "SP" [8,22,0,6] '','' = PVR (21.5)
#4 "Above20" [34,22,0,0] '','' = HYST (20,19)
#5 "Above20Out" [60,22,0,0] '','' = BO ()
>1:0 = {{2,0}}
>3:0 = {{4,0}}
>4:0 = {{5,0}}
}
[Const]
{
}
[Fin]
```

- CRLF line ends. The generator writes Latin-1, which the import takes; what EBO itself stores is UTF-8
  (2026-11-22, production exports). Header lines `#1,8,7` and `{41,27` copied from the shipped sample; their
  meaning is not known, and saved programs carry other numbers there.
- Block line: `#id "name" [x,y,0,flag] 'unit','description' = TYPE (parameters)`. Parameters in
  the order `MentaBlocks.xml` lists them. x,y are grid cells (a block about 26 apart in x and 16
  in y does not overlap). The flag is the three check boxes of the block dialog, see "The .aut format,
  second round".
- Connection: `>srcId:outPin = {{dstId,inPin}}`, pins counted from 0. The editor adds routing
  points and its own extra sections (`[InitialBindings]`, `[Ral]`, `[Entr]`, `[Dev]`, `[Print]`)
  on save; export a saved program to see them.
- BO / RO blocks become the program's public Outputs in WorkStation.
- All of these were tried later and work: expressions, RI / BI, constants, bindings, ALARM, PIDP (sections
  below). Still not generated: HFB (the format is known, see "What production programs showed").

## Loading a program a second time (2026-11-21)

- `Fb-Load` on a program that already has logic works: the import replaces the diagram without a question.
  `Ctrl+E` may then stop at the program's tab instead of starting the editor; `Fbe-Open` presses the pencil left of
  "Show Classic Mode" (automation id `ShowClassicMode`) when the editor has not come up after 14 s.
- **A re-import drops the program's own input bindings**: the RI / BI blocks get new GUIDs and read 0 until bound
  again. Bindings held by other objects that point at the program by path (another program's inputs, a graphic)
  survive. So after every reload: `Ws-Bind` the program's inputs again, then check.
- A failed `Ctrl+E` can leave an `SE.Graphics.Editor` process without a window; `Fbe-Open` removes it.

## File formats

- **Export file** (`.xml`): `<ObjectSet>` with `<MetaInformation>`, `<Types>` and
  `<ExportedObjects>`. An empty Function Block program exports as an `<ObjectType>` with
  `Base="menta.Program"` and a generated `udt.*` name, plus one `<OI NAME=.. TYPE=udt..>` holding
  `Task` (reference to `~/System/Tasks/Task 3`) and `Enabled`.
- A program with logic: its `menta.Program` type carries parameters `Complete`,
  `RequiredFBPEngine` (3.0), **`AutFile`**, `BinFile`, `MappingFile`. Each file parameter is
  `<InitValue><FileContents Size="n"><![CDATA[base64]]>`, and the bytes are **gzip**. `AutFile`
  gunzips to the program text, `BinFile` to the compiled code (starts with `COD3AA2` a few bytes
  in). Each module (HFB) is a second `<ObjectType Base="menta.Module">` with one `<Variable>` per
  public signal, and a nested `<OI ... declared="1">` with the values. The type name changes on
  every save (`udt.<a>.<b>`).
- So there are two routes for logic: (1) classic editor import of a `.aut`, which compiles;
  (2) an export xml with a new `AutFile`. Route 2 has no compiler in the loop (`BinFile`,
  `MappingFile` and the `Variable` list would have to match), so route 1 is the one to build on.
- Saved by EBO, the `.aut` text differs from the old sample: units are codes (`'0x10001'`), and
  public blocks carry a GUID as a third quoted field.
- **Menta program text** (`.AUT`): `[Aut]`, header lines, one line per block
  (`#n "name" [x,y,..] 'unit','' = TYPE (parameters)`), connections (`>src:pin = {{dst,pin}}`),
  `[Const]`, `[Fin]`. Samples: `WorkStation\STR350Config_*.AUT`.
- **Block catalogue**: `WorkStation\MentaBlocks.xml` (block names, input / output pins with types,
  parameters). Script language word lists: `WorkStation\AS*Intellisense.xml`.
  Help: `WorkStation\TAMenta.chm`, `WorkStation\Guide\SE.StruxureWare.Guide.pdf`.

## Bindings (2026-11-21)

- Bindings view of an object: select it, `Ctrl+B`. Every binding point has a box "Drop or type here to bind";
  a typed absolute path (`/Server 1/DH-ex2/TC1_DHW/TE1`) is accepted and stored relative (`../DH-ex2/...`).
  The path is object path + property: program / module / signal name; a program constant is program / name.
- Reach a point by typing its name in the quick filter. **A pending entry is dropped when the filter changes**,
  so `Ws-Bind` saves (toolbar Save, `ButtonSave`) after every point; about 5 s per point.
- **A program output block (RO / BO) cannot be read as a source**: binding an input to `.../TV1_OUT` is stored
  but flagged with a red mark and no value arrives. Bind inputs to public signals instead (the PIDA output
  `TV1`, a public expression, a public parameter). Program inputs (RI) take such a binding and follow it.
- An export in Standard mode carries only the bindings that stay inside the exported objects (and absolute ones
  to other servers); a binding to a neighbour object is left out. **Special mode keeps every binding**
  (`Ws-Export path file 'Special'`), Library mode only the inside ones (2026-11-22). The values in an export are
  live ones. What an export holds (2026-11-21): parameter blocks (PVR / PVB / PVI), constants,
  `FILT` outputs and the I/O blocks (RI / BI / RO / BO, under GUID names). **Public outputs of XPR / XPB / PIDA /
  LIMIT / SR / DELAY / CURVE are not in it.** To read a computed signal back, bind an RI of another program (or a
  graphic, or an MQTT data point) to it and read that.
- Binding points of a program's RI / BI blocks are listed by the bare block name (`TE1_IN`), also when the block
  sits in a module.
- The Bindings view of a program with many signals needs well over 5 s to open and is paged; `Ws-Bind` waits up to
  40 s and makes sure its tab is closed afterwards.
- Two BI blocks written as `BI ()` do not compile on the server ("I/O terminal reused in I/O block: ..."); the
  message comes from the editor started alone, the server-side editor only says compilation failed. **With the
  parameter list the editor itself writes, any number of BI blocks compile** (2026-11-22):
  `BI (4,,0,0,.5,0,,,0,0,100,0,0,0,0,0)`, and for RI `RI (0,3,,0,0.5,60,0,,0,0,100,0,0,0,0,0,40,0,)`. `aut.py`
  writes these by itself. (DH-ex2 was built before that and takes its binary commands as RI compared with 0.5.)
- **A public constant cannot be used inside an expression block** (compile fails; the editor help says the
  same). A private one can: fourth field of its `[Const]` line 0 instead of 1, `p.const(name, value,
  public=False)`. A private constant is not a property of the program object, so it cannot be changed from
  WorkStation.
- **Bindings by file** (2026-11-22), instead of about 5 s of typing per point: export the object in Special mode,
  write the bindings into the file (`ebox.py bind in.xml out.xml binds.json`), delete the object, `Ws-Import` the
  file: about 7 s for a compiled program with all its bindings, and the inputs follow at once. Works for a
  program and for anything else that exports its binding points. An import never replaces: with the old object
  still there the new one arrives as `Name_2`.

## Graphics (TGML) (2026-11-21)

- A Graphic object is type `tgml.TGML`; the drawing is a gzip + base64 `FILE` parameter in the export, each
  `Bind` name becomes a binding point (`PropertyReference`) of the object.
- Graphics Editor = `SE.Graphics.Editor.exe` (WinForms), opened with `Ctrl+E` on the graphic, window title
  `Graphic: <name> - Building Operation Graphics Editor`. Its toolbar is not reachable through UI Automation,
  so positions inside the editor window are used: File +36,+44 (New, Open, Save, Save As, Import..., Export...,
  Print, Properties, Settings, Close, Exit), Design +370,+44, Source +433,+44 (F7). `Ctrl+S` saves to the
  server, `Alt+F4` closes.
- `File > Import...` reads a `.tgml` but adds it as a new layer and keeps the page of the empty graphic
  (about 800 x 600), which crops a larger drawing. The **Source view** takes the whole document: `Ctrl+A`,
  paste, back to Design. `Gfx-Load` does that (root element with `Width`, `Height`, `Background`,
  `Stretch="Uniform"`; without the two `<?xml?>` / `<?tgml?>` lines).
- Elements used: `Rectangle`, `Line`, `Ellipse`, `Polygon`, `Text`, `Component` (takes attributes of our
  own, e.g. `Step`, `Val`). Colour by state: `<Bind Attribute="Fill" Name="X"><ConvertValue
  AttributeValue="#.." SignalLessOrEqualTo="0"/><ConvertValue ... SignalMoreOrEqualTo="1"/></Bind>`.
  Number in a text: `<Bind Name="X"><Script OnSignalChange="f"><![CDATA[function f(evt){ var t =
  evt.getTarget().getParentNode(); t.setAttribute("Content", new Number(evt.getValue()).toFixed(1)); }]]>
  </Script></Bind>`. Write a value: `setValue(bind.getFullBindName(), v)` from an `OnMouseClick` script
  (`evt.preventDefault()` first); `invoke(name, "EditProperties")` opens the object's dialog. Clicking a bound
  element without a script of its own opens WorkStation's change dialog.
- 205 shipped components and snippets were the source for these forms
  (`C:\ProgramData\...\Graphics Editor\Components`, `Snippets`): value displays, pumps, valves, exchangers.
- View a graphic: double-click it in the System Tree (`Ws-Open`).
- Generator: `scripts/tgml.py` (`Graphic.text/value/state/lamp/pump/valve/bar/step_button/pipe/rect`).

## MQTT (works, 2026-11-21): EBO -> Mosquitto -> FUXA, all on one machine

Nothing leaves the machine: the broker listens on loopback, and FUXA is kept to loopback by a Windows firewall rule
that blocks inbound 1881 (FUXA 1.3.5 ignores `uiHost`).

- **Broker**: Mosquitto 2.0.22, native Windows, service `mosquitto`, `127.0.0.1:1883`, anonymous. Silent install `/S`. Config `C:\Program Files\mosquitto\mosquitto.conf`
  ends with an "agent block" (listener, log); log `C:\agentwork\mqtt\log\mosquitto.log` shows every client and
  publish. Listening: **`ebo.sh mqtt [seconds]`** prints every "topic payload" the broker receives in that time.
  `mosquitto_pub.exe` is beside it.
- **EBO side**, three objects:
  `/Server 1/IoT` (New > `IoT Interface`) > `Broker` (New > `MQTT client`, at most 4 per interface) > `DH`
  (New > `Data Group`, at most 10 per client). Type definitions: `Enterprise Server\definitions\iot\*.xml`.
  - MQTT client, Properties > Connection: Host `127.0.0.1`, Enable TLS `No` (default Yes), Enabled `Yes`.
    Properties > Basic > Value format: `@(Value)`. **With an empty value format the client connects and
    publishes nothing.** Keywords offered by the "..." editor: `@(Value)`, `@(PropertyPath)`, `@(UnitText)`,
    `@(TimeNowIso)`, `@(TimeNowUnix)`, `@(Status)`, `@(Quality)`, `@(PointId)`, `@(ServerName)` and more, so a JSON
    payload is a matter of writing it around them. Paste the text; typed through SendKeys the `@(` came out as a GUID.
  - Data Group: Event driven `Yes` (delta 0.5), Enable interval `Yes`, Interval 10 s, Data points = list of
    object + property picked in "Select Object and Property". Topic empty = EBO path: `Server 1/DH-ex2/TC1_DHW/TE1`.
    Payload with `@(Value)` is the plain number (`59.266933441162109`).
  - The Status field of the client kept showing Offline in the open property page while the broker log showed it
    connected; trust the broker log.
  - Not tried: the other direction (Allow subscription on the group, MQTT Points under the client), retained
    messages, last will, JSON payloads.
- **Driver**: `Mq-Client parent name [host] [format]`, `Mq-Group client name points [seconds]` with points =
  `@(@(@('Prog','MODULE'),'Signal'), ...)`, `Mq-Points points` (adds to the group page on screen), `Mq-Listed`
  (paths in its Data points list), `Dp-Pick` (one row of the picker), `Prop-*` helpers. Both functions reuse an
  object that already exists. Any public signal can be a data point, computed ones included. Property page labels and picker rows carry no UI Automation names:
  fields are taken by kind and order, and a picker row is identified by clicking it and reading the Path box.
  The Path box of the picker cannot be typed into. The "+" of Data points has automation id `AddButton`.
- **A property page that opens into a fresh work area tab is drawn but not exposed to UI Automation** (no combo
  boxes, no `PropertyGridContainer`); seen after a WorkStation start and after creating an object. Selecting
  another object and the first one again in the same tab exposes it. `Prop-Grid` does that by itself.
- **FUXA 1.3.5**, as it was set up without internet access (with internet, `npm install -g @frangoteam/fuxa` and
  `fuxa` do the same): portable Node.js 22 (`C:\agentwork\node`) and `@frangoteam/fuxa` with its
  `node_modules` packed on another machine for Windows (`npm_config_platform=win32 npm_config_arch=x64 npm install
  @frangoteam/fuxa --os=win32 --cpu=x64`, then delete `@serialport/bindings-cpp/build`, which holds that machine's binary
  that would be preferred over the Windows prebuild). App `C:\agentwork\fuxa\app`, data
  `C:\agentwork\fuxa\data` (`--userDir`), started at boot, log
  `C:\agentwork\fuxa\fuxa.log`, `uiHost: "127.0.0.1"` in `data\_appdata\settings.js`, page
  `http://127.0.0.1:1881/`. A project is loaded with `POST /api/project` (json body, no log-on in this set-up).
  MQTT device = type `MQTTclient`, `property.address` `mqtt://127.0.0.1:1883`; a tag per topic: type `raw`,
  `address` = `memaddress` = topic, `options.subs` = [topic].
- **FUXA generator: `scripts/fuxa.py`** (`Fuxa.tag / text / box / line / value / lamp / save`), load with
  **`ebo.sh fuxa <project.json>`**, show with `Web-Top 'http://127.0.0.1:1881/' 'FUXA' x y w h`. View item forms
  (read from the client bundle `...\@frangoteam\fuxa\dist\main.*.js`): a live number is `<g type="svg-ext-value">`
  with one `<text>`, a lamp is `<g type="svg-ext-gauge_semaphore">` with one `<ellipse>` and colour ranges.
  `fractionDigits` 1 and up is applied, 0 is ignored, a unit in `ranges[0].text` is not drawn: put units in labels.
  The view is centred in the window; a window narrower than view width + 40 or lower than view height + 90 clips it.
- **Stopwatch** over the taskbar clock: `Timer-Start [seconds already run]`, `Timer-Stop` (freezes, turns white),
  `Timer-Close` (`win/timer.ps1`, topmost, never takes focus). `Ws-Close` leaves the bare desktop; `Web-Top` opens a
  page in its own Edge window kept above WorkStation (call it again to bring an existing one back), `Web-Back`
  takes such windows out of the way. A window kept on top lies over the log-on form, so `Ws-Ensure` (`ebo.sh
  logon`) calls `Web-Back` first: after a log-on, call `Web-Top` again.
- WorkStation logs off after **5 idle minutes**: `System/Domains/Local/Groups/Administrators`, Policies tab,
  "Automatic logoff". The field is locked for this built-in group (type default would be 10 minutes; choices 1
  minute ... 2 hours, Never). Not changed. `ebo.sh logon` before a block of work costs nothing when already on.

## Open

- Read computed public signals back by script (the Variables view through UI Automation). A server value
  (`server.point.AV`) bound to the signal can be made from a file now, but its value was absent from the export.
- I/O modules and real field devices; outputs written to targets.
- Clicks on the graphic by script use fixed screen positions (1600x1200, default panes).
- Script program round trip.
- HFB (hierarchical blocks) written by the generator (format known), TSCH blocks, schedules from a file.
- Whether the alarms and trend logs made from a file behave (they import and show; no alarm was tripped and no
  log was read back).
- Navigation between graphics (`Link`), status colours (`ConvertStatus`): seen in production graphics, not
  generated.
- MQTT in the other direction: a value written into EBO from the broker (section MQTT).

## The driver (scripts/ebo.sh, win/lib.ps1, win/ebo.ps1), 2026-11-21

`ebo.sh` never reads standard input, so it can be called inside a `while read` loop. One call at a time: two
drivers on one desktop type into each other's windows.

`ebo.sh setup` makes the work folder `C:\agentwork\ebo`. `ebo.sh run '<powershell>' [seconds]` prints what the commands write. An error shows as `EXC:`
with the stack, and the output before it is kept.

| Function | Does |
|---|---|
| `Ws-LoggedOn`, `Ws-Ensure [user]`, `Ws-Logon [user]` | log-on state; start WorkStation and log on (used by `ebo.sh logon`, which supplies the password file) |
| `Ws-Select '/Server 1/X'`, `Ws-Refresh` | select a System Tree item (expands parents), `F5` |
| `Ws-New parent 'Function Block Program' name` | New Object dialog: filter, pick type, name, Create (about 6 s) |
| `Ws-Delete path` | Delete key, answers `Confirm Delete` |
| `Ws-Export path file [mode]` | context menu `Export...`, preview, Save As, result (about 15 s). mode `Standard` (default), `Special` (keeps every binding) or `Library` |
| `Ws-Import parent file` | `File > Import...`, file dialog, preview, Import, Close (about 7 s). Throws the preview's messages when it counts an error |
| `Fbe-Open path` | `Ctrl+E` and wait for the editor window (about 17 s) |
| `Fbe-Import $p file`, `Fbe-Save $p`, `Fbe-Exit $p` | editor File menu by command id; Save waits out "Generating application..." (about 5 s) and throws the editor's message on a compile error |
| `Fb-Load parent name file` | create if missing, open, import, save, exit |
| `Menu-List hwnd`, `Menu-Do hwnd menu item` | any menu command of the editor, e.g. `Menu-Do $p.MainWindowHandle 'Zoom' 'Zoom Out 200%'` |

What was learned building it:

- WorkStation is WPF and exposes nearly everything to UI Automation: tree items are named `/` + object name
  (not the full path), dialogs have automation ids (`FilterInfoTextBox`, `TextBox`, `LogOnButton`), the address
  bar is an edit box `PART_PathText`.
- The Function Block editor is a classic Win32 program: its menu can be read with `GetMenu` and a command sent
  with `WM_COMMAND`, which needs neither focus nor coordinates. File menu when started from WorkStation: Save
  (13), Import, Export, Print, Exit (16). Started alone it has New, Open, Save, Save As instead.
- **Started alone** (`tam32.exe` with the WorkStation folder as working directory) the editor needs no server
  log-on: `File > Open` reads a `.aut`, `Options > Simulate` compiles it and shows live values. That is the
  quick syntax and compile check for a generated file.
- Bringing a window to the front: `SetForegroundWindow` is refused unless the caller has just produced input.
  A tap of F24 lifts that. Alt also does, but leaves the target's menu bar in keyboard mode. Clicking the
  taskbar button of a window that is already in front minimises it.
- `Process.MainWindowTitle` of WorkStation goes empty after a dialog; windows are found by listing the desktop.
- The file dialog's File name box takes no UI Automation value; `Alt+N`, typed path, Enter works.
- The question after an import of a foreign file and the file dialog are both titled `Import`. The file dialog
  has an element with automation id `1148`, the question has not.
- Saving an empty diagram gives a box titled `Tam32`: "Error: Compilation of program failed."
- WorkStation logs itself off after some idle minutes. Classic Mode stays on across log-ons.

## The .aut format, second round (2026-11-21)

Sources: 256 files of the shipped macro library
(`C:\ProgramData\...\WorkStation\Function Block Editor\Macro Block Library`), the editor help
(`TAMenta.chm`), and a calibration sheet.

- Expression blocks take braces: `XPB {A<-45|A>50}`, `XPR {f?B:A}`, `XPI {e?1:3}`. Capital letter = analog
  input, lower case = binary. Inputs are pins in alphabetical order. Operators: `! * / % + - << >> < > <= >= =
  != & ^ |`, `a ? b : c`, functions `LN LOG EXP COS SIN TAN ACOS ASIN ATAN SQRT ABS INT`, `x**y`.
- Flag (last number in the brackets) = the three check boxes of the block dialog (2026-11-22, editor help
  "Configure a Function Block" and production programs): **1 Public, 2 R/W, 4 Backup**. So PVR 7 = public,
  writable, kept over a power failure; 3 = the same without backup; 6 = private. SR 4 / 5, ALARM 5, DELAY 0 / 1
  / 5, SHR 4 / 5, ACCUM 6, PIDA 3 / 6 / 7, PIDP 3. `aut.py`: `block(..., public=, rw=, backup=)`.
- A name with a backslash, `MODULE\Signal`, puts the block in a module; modules show as groups in WorkStation.
- Constants: `[Const]` lines `Name~value~'unit'~public~1~''` (public 1 or 0; the fifth field is 1 or 17,
  meaning not known). A constant name can stand where a block parameter
  goes: `DELAY (DHW_ALM_DLY,0)`, `FILT (TOUT_FILT_T)`, `LIMIT (TS_MIN,TS_MAX)`, `CURVE (1,-20,CRV_N20, 0,CRV_0)`.
  In WorkStation they come out as properties of the program object, so they can be changed there.
- `CURVE (limit, x1,y1, x2,y2, ...)`. `PIDA (ControlInt,UMin,UMax,StrokeTime)`. `ALARM`, `TSCH`, `AI`, `AO`,
  operators (`Op?:`, `OpR @ (0.5)`, `OpW (1)`) have examples in the macro library.
- **Pin numbers are not always the order drawn.** PIDA: MV 0, SP 1, Mode 2, TSg 3, G 4, Ti 5, Td 6, DZ 7, drawn
  as MV, SP, Mod, G, Ti, Td, DZ, TSg (from `Heating/Control/HOTWATER.AUT`). Wiring by drawn order compiles and
  runs with gain, integral time and tracking signal on the wrong inputs; crossed wires at the block are the tell.
- PIDA mode: 0 off (output follows TSg), 1 normal, 2 forced to UMax, 3 forced to UMin. e = SP - MV, positive
  gain = heating. Gain = 100 / proportional band.
- **PIDA: wire the block's own output back to TSg** (2026-11-21). The block adds each cycle's step to the tracking
  signal; with TSg left at a constant 0 the output sits at one step (a few percent) and never integrates. With the
  output fed back it behaves as a PI controller. A controller that must give 0 % while disabled: mode 3 (forced to
  UMin = 0), not mode 0, since TSg now carries the output. `aut.py` routes the self-wire.
- SR toggles each cycle when set and reset are both true.
- Wires: `>src:0 = {{dst,pin}}` direct; `{{x,y;x,y;dst,pin}}` with corner points; fan-out
  `{{jx,jy{branch}{branch}}}` where each branch is points and a destination. A wire point is drawn one cell
  above its y: to meet a pin at block y + 5 the point needs y + 6.
- Grid: 5 px per cell at 100 %. Sizes in cells (w x h, input pins from the top, output): standard block 10 x 10
  (1 pin at 5; 2 at 2, 8; 3 at 1, 5, 9; output 5); expression with n >= 4 inputs 3n - 1 high, pins at 1 + 3k;
  expression width max(10, ceil(1.5 * length + 2.5)); two-parameter blocks (DELAY, LIMIT, HYST, OSC, CURVE)
  10 x 14, pin and output at 7; PIDA 15 x 27, pins at 3 + 3k, output 14; SR 12 x 10; RO / BO 10 x 6 plus an
  output stub; RI / BI have 8 cells of input stub left of the body; AND / OR 6 x 6; constant operators 9 x 3
  with the output at the top.
- RI / BI / RO / BO are accepted in a program on the Enterprise Server (the help says Xenta 700 only). In an
  export their values appear under GUID names.

## Generator (scripts/aut.py)

`Program.block(type, name, params, unit, public, module, rw, backup)`, `Program.const(name, value, unit, public,
bind)`, `Program.alarm(name, src, text, delay_on, delay_off, priority, module)`, `Program.wire(src, dst, pin)`
with pin a number, a PIDA / PIDP / SR / SHR / ACCUM pin name or an expression letter. A unit given as `°C`, `%`,
`Pa`, `s` or `ppm` is written as EBO's unit code; RI and BI get the parameter list the editor writes. Block
sizes and pin rows come from the catalogue (shape and offsets in pixels, 5 per cell), which agreed with every
hand measurement and with the wire end points of 1900 production blocks; only expressions, I/O blocks, PIDA and
the constant operators are worked out in the code. `save()` lays out
and routes: columns by signal depth shared by all modules, one band per module, set values one column before
their first reader, every wire in right angles through a channel between columns and, when it skips columns or
changes band, a lane above the destination band. Block and parameter counts are checked against
`reference/MentaBlocks.xml`. An expression whose pin order would depend on how capitals sort against lower case
is refused. `expected()` gives what an export must show.

## What production programs showed (2026-11-22)

Source: exports of a running EBO 3.2 site (14 Function Block programs, 15 to 490 blocks each, two Script
programs, 15 graphics, about 150 alarms, 230 trend logs). Read with `scripts/ebox.py`. Everything marked
"tried" was loaded into EBO 7.1 afterwards.

- **PIDA and PIDP both have their own output wired to TSg**, in every loop (17 + 4), and the mode comes from
  `XPI {a?1:3}`: the two traps found the hard way are simply how it is done. PIDP numbers its pins in the order
  drawn: MV 0, SP 1, Mode 2, G 3, Ti 4, Td 5, DZ 6, TSg 7 (tried).
- **ALARM block**: `ALARM (DelayOn,DelayOff,Priority,'guid','','alarm text','reset text')`, one binary input,
  flag 5. On the server it becomes an `alarm.ChangeOfStateAlarm` object below the block's module, named as the
  block, with message, priority and delay taken from the parameters and the monitored signal bound (tried, with
  the fourth field left empty). So a program brings its own alarms: no clicking, and they survive a reload.
- **Constant bindings travel in the file**: section `[InitialBindings]` after `[Const]`, one line
  `ConstantName;../Folder/Object/Property` per public constant. Tried: the constant took the value of the
  other program's signal right after the load, and the binding shows in a Special export. A line naming an RI
  block is kept by the editor but has no effect. `p.const(name, value, bind='../X/M/Signal')`.
- **HFB** (hierarchical block): the line `#n "Name" [x,y,0,0] '0x10001','' = HFB {}` is followed by `{`, the
  inner diagram (block lines and wires, **ids starting again at 1**, further HFBs nested the same way) and `}`.
  Inside, `HFAI` / `HFDI` are the analog / binary inputs and `HFAO` / `HFDO` the outputs, named; outside, the
  HFB's input pins and outputs are numbered `0, 1, ...` (`>2:1 = ...` is the second output). Modules are a
  separate thing: a block inside an HFB still carries `Module\Name`. Not generated yet.
- **Expressions**: inputs need not be consecutive letters (`XPB {(A>=Z)&(A<=X)?1:0}` has pins A, X, Z); private
  constants by name (`XPB {A<MinTemp|@A>MaxTemp}`); an `@` inside the text is only where the editor breaks the
  line on the block.
- **Wires**, complete grammar: `>src:out = {group group ...}`. A group is `{points;dst,pin}`; a fan-out is
  `{points{branch}{branch}}` with branches nested as deep as needed; several groups side by side all start at
  the output. A path ending in `x,y.` is an open end (a stub drawn to nowhere). `>0 = x,y,N {{x,y;...}}` lines
  are frames drawn around a group of blocks, no signal.
- **Other blocks met**, all in the catalogue and now laid out from it: `PRCNT (v0,v100)` (0 ... 100 % between two
  values), `SHR (init)` sample and hold (pins D, c), `TRIG (mode)` one-cycle pulse (0 / 1 rising, 2 falling,
  3 both), `RAMP (rate)`, `ACCUM (init)`, `DELB / DELI (init)` one cycle delay, `MAX ()`, `MIN ()`, `NOT ()`,
  clock blocks `HOUR () SECOND () MONTH () WDAY ()` for time conditions, operators `Op?:` and `Op:?`
  (multiplexers), `Op+ Op- Op/ Op> Op< Op= Op<= Op&& Op!!`. An RO can be read inside its own program (it has
  an output).
- **Unit codes** seen: `0x10001` none, `0x280001` °C, `0x200001` %, `0x200002` ppm, `0x230002` Pa, `0x2e0007` s;
  `0xf0001` on air flows and `0x170001` on humidity (exact unit not checked). Tried: the import takes the codes.
- After a save the file also has `[Ral]` (ends with `1,1000`: cycle time in ms), `[Entr]` (one `@"name",...`
  line per RI, `$"name",...` per BI), `[Dev]`, `[Print]`. None of them is needed in a file to import.
- Habits worth copying: modules named `Inputs`, `Outputs`, `Alarms`, `SP`, then one per loop; every setpoint a
  public PVR; sensor fault alarm = `XPB {A<MinTemp|@A>MaxTemp}` into an ALARM block per sensor.

## Objects from a file (works, 2026-11-22)

Objects of built-in types need no type definition in the file, only `<OI NAME= TYPE=>` with `<PI Name= Value=>`
values and `<PI><Reference Object= Property=/></PI>` bindings. A file written by `scripts/objects.py` and loaded
with `Ws-Import` gave, in 7 s: a folder, an interval trend log, a change-of-value trend log, a trend chart of
both, a change-of-state alarm, an out-of-range alarm, a deviation alarm against a setpoint signal, and analog /
binary / string server values, all bound to signals of a program. Read back with a Special export: values and
bindings as written.

- File frame: `<ObjectSet ExportMode="Special" Note="TypesFirst" Version="7.1.1.132">`, `<MetaInformation>`
  (ExportMode, RuntimeVersion, SourceVersion, ServerFullPath), `<ExportedObjects>`. A `<Types>` block is needed
  only for objects with generated types (programs, graphics, menus).
- A `Reference` is relative to the object that holds it: `Object="../../Program/MODULE" Property="Signal"`; a
  reference to an object as such (a log shown in a chart) has no `Property`.
- Types and properties (from the production exports):
  `trend.TLog` Interval (ms), LogSize, Enabled, LogPoint -> signal;
  `trend.TLogChangeOfValue` DeltaValue, LogSize, Enabled, LogPoint;
  `trend.view.GraphicalTrendView` with one hidden child `trend.view.TrendLogSeriesProperties` per curve
  (DisplayLog -> the log, Color);
  `alarm.ChangeOfStateAlarm` MonitoredVariable, AlarmMessage, ResetMessage, AlarmPriority, ResetPriority,
  TimeDelayToOffNormal (s);
  `alarm.OutOfRangeAlarm` HighLimit, LowLimit, HighLimitMessage, LowLimitMessage, ResetMessage, priorities,
  TimeDelayToOffNormal, Deadband;
  `alarm.OutOfReferenceRangeAlarm` HighDiffLimit, LowDiffLimit, SetpointReference -> signal;
  alarms also take Category -> `~/System/Alarm Control Panel/Alarm Handling/Categories/<name>` (the category
  itself travels in a `<SupportingObjects Container=...>` block after the objects) and ShuntPoint -> signal;
  `server.point.AV / BV / SV` Value (a number, or a binding);
  `schedule.NSPDigitalSchedule`: hidden children `WS00001` ... `WS00007` (`DailySchedule`, DayOfWeek) each with
  `TVP0000n` time-value pairs (Hour, Minute, Value; `Null="1"` ends an entry). Not generated.
  `webservice.genericconsume.SimpleXml` (URL, PollingInterval) with child points (XPath) reads values from a
  web service. **Its URL holds the service's access key in plain text**, and so does every export of it.
- WorkStation's File menu also has `Import from xlsx...` (not looked into).
- A whole program or graphic comes in the same way from its own export, compiled code included, so a program
  built once can be put on another server without the editor.

## Reading an export (scripts/ebox.py), 2026-11-22

`ebox.py tree | binds | unpack | aut | bind`. `unpack` writes each program's text (`.aut`, with a summary:
blocks by type, modules, HFBs, alarm blocks, bound constants), each graphic (`.tgml`), each Script program's
source (`.txt`) and attached documents.

- A **Script program** is type `script.Program`; parameter `File` holds an XML text `<PEObject ...>` with
  `<Code>` (base64 of the source), `<ByteCode>` and `<BindingVars>` (name, line, kind). Inputs and outputs are
  `<Variable>` entries of the type and bind like any other point.
- The export of a program in a module-structured site shows RI / BI values under the block name in the module
  that holds them (`Inputs`), with their bindings in Special mode.
- A server backup (`.xbk`) is a zip: `Configuration/configuration.db` and `Historical/*.db` (SQLite), licence
  and domain files, and the server version in a file name (`3.2.2.61.serverrevision`). Not opened further; a
  backup holds the user database, so treat it as a secret.
- Trend log data exported from a chart is CSV: `"Time stamp","Value","Events","Comment","User"`, time and decimal
  comma in the locale of the WorkStation that wrote it.

## Graphics seen in production (2026-11-22), not yet in tgml.py

- Root attributes `UseGlobalScripts="True"`, `DisablePanAndZoom="True"`; content in `<Layer>` elements.
- Navigation: a `<Link Name="..."/>` inside a component is a binding point for an object (another graphic, a
  trend chart). A click on the component opens it; scripts do the same with
  `invoke(link.getFullBindName(), "ViewObject")`. Other commands used with `invoke`: `OpenInNewWindow`,
  `OpenInSelf`, `EditProperties`.
- Status of a value, not only the value: `<ConvertStatus Error="#FF6000" Forced="#FFD100" Stored="#42B4E6"/>`
  inside a `Bind` sets a colour by state; in a script `evt.getStatus()`, `evt.getUnit()`.
- `<TargetArea>` gives a component an invisible click area (plus / minus boxes of a setpoint stepper),
  `<Animate>` runs colour and size transitions on mouse over, `<TextBox>` is text with a frame and alignment in
  both directions, `<Expose ExposedAttribute= Name=/>` makes an attribute of an inner element a property of the
  component. Events used: OnDocumentLoad, OnSignalChange, OnMouseClick / Over / Out / Down / Up / Move.

