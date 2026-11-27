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
- `Show Classic Mode` on (it stays on across log-ons; the driver switches it on when it finds it off).
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
  does nothing for a server address other than the one asked for. Unanswered, the log-on ends with "Logon has
  timed out".
- Another server: `EBO_SERVER=<address> ebo.sh logon`; a new server: `ebo.sh firstlogon` (section "Servers in
  containers").
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
  - The other direction (broker -> EBO) works: section "MQTT subscription: values from a broker into EBO".
    Not tried: retained messages, last will, JSON payloads on publish.
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

## MQTT data groups from a file, and a delete that hit the parent (2026-11-22)

- A Data Group is `iot.DataGroup` with `<PI Name="DataPoints">` holding one `<Reference Object= Property=
  DeltaFilter="0" Retransmit="0" TransferRate="10"/>` per point (Object relative to the group), and the values
  EnableInterval, EventDriven, Interval. `objects.py` `mqtt_group()` writes it; import below the MQTT client
  (`ObjectSet(parent='/Server 1/IoT/Broker')`). 92 points in three groups came in in 40 s and all 92 topics
  arrived. The MQTT client itself (`iot.StandardMQTT`: URL, EnableTLS, ValueFormat) comes back from its own
  Special export the same way.
- Picking data points in the dialog (`Mq-Group` / `Mq-Points`) is only safe for small modules: on modules with 60
  to 70 signals it picked neighbouring rows (32 of 92 right, 26 wrong ones added).
- **`Ws-Delete` deleted the parent twice**: three deletes in a row under one node, the tree still refreshing, the
  click that gives the tree focus landed on the parent row, and DEL removed the whole MQTT client. Since then
  `Ws-Delete` presses DEL only when the wanted item is the selected one, retries when the item is not found for a
  moment, and refuses a path that ends in a slash. Six deletes in a row under one folder then left the parent alone.
  Before deleting several children of an object that cannot be rebuilt from a generator, export it first.

## MQTT subscription: values from a broker into EBO (works, 2026-11-23)

Seen on EBO 7.1.1.132 Enterprise Server, Mosquitto on the same machine, all objects made from import files.

- **Where it lives**: on the MQTT client (`iot.StandardMQTT`), tab Subscription: `SubscriptionTopic`, `SubQoS`, and
  JSON pointers `JsonPtrPointID` (default `/pointId`), `JsonPtrValue` (default `/value`), `JsonPtrCommandRoot`
  (an object or an array of command objects), `JsonPtrCustomData1/2`, `JsonPtrCommandData1/2`. Response settings
  (`SendResponse`, `ResponseTopic`, `ResponseFormat`) not tried. The Data Group (`iot.DataGroup`) has
  `AllowSubscription` (**must be Yes**), its own `SubscriptionTopic`, `MaxAllowedUpdateRate`, `MinAllowedValue`,
  `MaxAllowedValue` (those four not tried).
- A subscribed message is a "command": the point id pointer names a data point of a group with Allow subscription
  = Yes, the value pointer gives the value, and the value is written to that data point (a server analog value
  `server.point.AV` in the tests). **Both pointers hold for the whole client**, not per group or per point.
- Point ids EBO accepts (each seen to write the value):
  - the id the keyword `@(PointId)` publishes, form `nspg:<22 chars>.<22 chars>//Value`;
  - the full property path with leading slash, `/Server 1/Folder/name/Value`. **Without the leading slash the
    message is ignored**;
  - the target object's Foreign address (`ForeignAddress`, a property every object has; in an import file
    `<PI Name="ForeignAddress" Value="..."/>` on the value; the keyword `@(ForeignAddress)` publishes it).
- Not working:
  - empty `JsonPtrPointID` with a single data point: the client connects and never sends SUBSCRIBE;
  - topic only on the group, the client's topic empty: no SUBSCRIBE either;
  - an `iot.point.AV` ("Analog MQTT Value") below the client with a foreign address: imports, took no value.
- The client subscribes without any publishing group; the SUBSCRIBE shows in the broker log a few seconds after the
  import. Trust the broker log, as for publishing.
- **A message with several values and no point id per value** (ChirpStack v4 uplink event from a LoRaWAN network
  server, topic `application/<app>/device/<devEui>/event/up`, values under `/object/<key>`, device under
  `/deviceInfo/devEui`): point id pointer `/deviceInfo/devEui`, every target value gets the devEui as Foreign
  address, and since the value pointer is per client, **one MQTT client per value** (`JsonPtrValue`
  `/object/temperature`, `/object/humidity`, ...), each with one Data Group (Allow subscription Yes, EventDriven 0,
  EnableInterval 0, so it publishes nothing) holding its one target. Three clients on one topic, three values with
  the same foreign address: each client wrote only its own group's point (27 / 23 / 3678 from one message).
  Limit: 4 MQTT clients per IoT Interface; a second IoT Interface on the same server was accepted, so 4 more values
  per extra interface. `objects.py` `mqtt_subscriber()` writes client and group; generator
  `examples/lora-mqtt/make.py` (values file + IoT file, both imported below `/Server 1` with `Ws-Import`).
- **Import trap: IoT Interface and folder with the same name in one server.** The second import is renamed
  `<name>_2`, and the data point references of its groups (relative, `../../../<name>/x`) resolve inside the
  imported set, to the client itself (export shows `Object=".."`): clients connect, nothing subscribes, nothing
  publishes. Give the interface and the value folder different names.
- Testing without waiting for a device: `mosquitto_pub.exe -h 127.0.0.1 -t <topic> -f <file>` on the EBO machine,
  payload in a file (no JSON quoting on the command line).
- Reading the values in WorkStation: right-click the column header row of a folder's list view > `Add/Remove
  columns` > tick `Value` (and `Foreign address`); live values then show in the list. The star button in the list
  toolbar saves the layout (not tried by script). At 1600x1200 with default panes: header right-click at about
  x 600 y 237, menu item 690,251, dialog check boxes `Value` 649,634, `Foreign address` 649,482, OK 841,759.
- **Column layout is per folder**: the Value column has to be added again in each folder. Where the dialog has
  many column choices (a BACnet device's Application folder: `Value` is below the visible part of the list), type
  `Value` into the dialog's quick filter (click it at about 800,419 at 1600x1200); the one remaining check box is
  then at 649,464, OK 841,759.
- **Proven against a real network server broker (2026-11-23)**: a LoRaWAN network server with a ChirpStack-format
  broker, anonymous, plain TCP 1883, QoS 0, nothing retained, one uplink per 10 minutes. The three clients opened
  three TCP connections within about 20 s of the import and stayed up. The next uplink (`object` humidity 27,
  temperature 22.9, vdd 3684) arrived in the three values as 27,00 / 22,90 / 3 684,00; the same sensor read over
  BACnet/IP from the same network server showed 27,00 % Rh / 22,90 °C / 3 684,00 mV at the same moment: the two
  ways agree.
- Nothing is retained on such a broker, so after an import or a server restart the values stay at their initial
  0 until the next uplink. A value gets a unit only if the import file gives it one (next bullets; BACnet values
  bring theirs).
- **Units from the file (2026-11-24)**: attribute on the Value property, `<PI Name="Value" Unit="0x280001"
  Value="0"/>`; the export gives it back the same way. Codes: section "What production programs showed", Unit
  codes. `objects.py` `value(..., unit=, foreign=)` and its `UNIT` map write unit and Foreign address.
- **Trap: a subscribed number into a value whose unit has a prefix is taken as the base unit** (2026-11-24): 3678
  into a mV value showed 3 678 000 mV. Client property `ScaleToBaseSIUnit` = 0 (default 1) stops it: 3660 then
  arrived as 3 660 mV. °C and % Rh values were the same either way. `mqtt_subscriber()` always writes
  `ScaleToBaseSIUnit` 0. `ConvertValuesToSI` left at its default, not tried.
- **Many values from one message with one client: a list of command objects** (works, 2026-11-27). Client
  property `JsonPtrCommandRoot` points to a JSON array (`""` = the message itself is the array, `/c` = the array
  under key `c`); `JsonPtrPointID` and `JsonPtrValue` are then read inside each item. Payload
  `[{"id":"t.a","v":1.5},{"id":"t.b","v":-2.25}]` with `JsonPtrPointID` `/id`, `JsonPtrValue` `/v` wrote both
  values (targets found by Foreign address, both in the client's group with Allow subscription Yes). An item whose
  id matches nothing is skipped, the others are still written. One client took 235 items (about 6 kB) into 219 values
  (spot price example, `examples/spot-price`). This lifts the "one client per value" limit whenever the
  publisher can send such a list.
- **Trap: a Special export does not carry Foreign addresses**, so the bind round trip (Special export, `ebox.py
  bind`, delete, import) gives back values **without** them, and a subscribing client that finds its targets by
  Foreign address writes nothing, without any message. Put them back into the bound file before the import
  (`examples/spot-price/add_foreign.py`), or import such values after the round trip.
- Pointers outside `object` work the same (2026-11-24): `/rxInfo/0/rssi` (array index in a JSON pointer) gave the
  first gateway's radio level (-87), `/fCnt` the uplink counter. Five signals = four clients on one IoT Interface
  plus a fifth on a second interface; `make.py --signals name=/json/pointer[@unit],...` (default temperature,
  humidity, vdd, rssi, fcnt) starts `<iot>_2`, `<iot>_3` after every four. All five arrived from one message, on
  a local Mosquitto and from the real network server broker (22,3 °C, 26 % Rh, 3 678 mV, -87, 7163).
- **Reading the values by script** (2026-11-24): a Special export of the folder of values (`Ws-Export '<folder>'
  file 'Special'`, then `ebo.sh get`) holds the live `Value` (and `Unit`) of each `server.point.AV` at the moment
  of the export, about 20 s per read. That is the scripted read-back, instead of screenshots. The Foreign address
  is not in that export.
- The Value column added to a list view was gone after the next log-on: the layout is not kept unless saved (star
  button, not tried).
- **Staleness** (2026-11-24): the uplink counter changes with every uplink, also when no reading does, so it is
  the input for "is the sensor still reporting". The room-sensor age program (`examples/room-sensor/make_age.py`
  -> `SensorAge.aut`, inputs V1..V3, outputs `Age_Min`, `Stale` after 30 min) loaded with `Fb-Load '/Server 1'
  '<name>_Age' ...` and bound with `Ws-Bind '<program>' @(@('V1','<folder>/fcnt/Value'),
  @('V2','<folder>/temperature/Value'),@('V3','<folder>/humidity/Value'))`: 2,4 min after an uplink `Age_Min`
  showed 2,43 and `Stale` False. With V1 on the counter the program's "last change, not last report" limit does
  not apply. An alarm on `Stale` from a file (`alarm_state(None, 'Stale_Alarm', '<program>/Stale', text=...)`,
  `ObjectSet(parent=<value folder>)`; `examples/lora-mqtt/make_alarm.py`) imported. **It trips and
  resets** (2026-11-24, copy of the set on a broker of our own with the limit at 1 minute: one uplink, 80 s later
  Alarm state `Alarm`; next uplink, within seconds `Reset`). Alarm state by script or eye: in the list view of the
  folder holding the alarm, Add/Remove columns > `Alarm state` (check box at 649,558 at 1600x1200).
- A program's own values in WorkStation: select the program, tab Variables, click the "+" of the first row (about
  286,332 at 1600x1200): Inputs and Public Signals with live values.
- Deleting and importing the clients and values again is harmless: the values come back with the next uplink.
- The EBO machine needs outbound TCP 1883 to the broker only; no inbound rule (unlike BACnet/IP, where answers
  arrive as new flows).
- A network server of this kind may forbid outside clients to publish on its uplink topic and feed its own
  Modbus/BACnet side from that topic: do not test by publishing there. Rehearse on a broker of your own with a
  copied uplink payload, then point the clients at the real one.

## WebStation in the Brave browser (2026-11-22)

- A graphic shows live values in WebStation, but **clicks on it do nothing** (buttons, values) while Brave Shields
  has "Block fingerprinting" on, which is the default. Seen with a button of `tgml.py` and reported the same from a
  production system. Fix per site: lion icon in the address bar > Advanced options > Block fingerprinting off;
  Shields itself can stay up. Tested three ways on one graphic: default, no click; Shields down, click works;
  Shields up with fingerprint blocking off, click works. Edge and Chrome do not have the problem.
- Cause not proven; the likely one is that WebStation finds the clicked element by reading canvas pixels back,
  which that protection disturbs on purpose.

## Open

- Read computed public signals of a program back by script (the Variables view through UI Automation). A server
  value (`server.point.AV`) bound to a program signal can be made from a file, but its value was absent from the
  export; a server value written by MQTT is present in a Special export (section "MQTT subscription", read by
  script), so plain server values can be read by script now.
- Real field devices: download to a connected MP-C / RP-C, live I/O. (Points, terminals and bindings are made.)
- Clicks on the graphic by script use fixed screen positions (1600x1200, default panes).
- Script program round trip.
- TSCH blocks, schedules from a file.
- Alarms made from a file: a change of state alarm trips and resets (section "MQTT subscription", stale alarm);
  range and deviation alarms not yet seen tripping.
- Navigation between graphics (`Link`), status colours (`ConvertStatus`): seen in production graphics, not
  generated.
- A component file written by `save_component` was not yet opened from the Graphics Editor's Components pane.
- Dashboard widgets not tried: point table, pie, heat map, period over period, consumption, Sankey, group.
- MQTT subscription (section "MQTT subscription"): response messages (`SendResponse`, `ResponseTopic`),
  the group's update-rate and min/max filters, string and binary targets, `ConvertValuesToSI`, a command root with
  an array.

## The driver (scripts/ebo.sh, win/lib.ps1, win/ebo.ps1), 2026-11-21

`ebo.sh` never reads standard input, so it can be called inside a `while read` loop. One call at a time: two
drivers on one desktop type into each other's windows.

`ebo.sh setup` makes the work folder `C:\agentwork\ebo`. `ebo.sh run '<powershell>' [seconds]` prints what the commands write. An error shows as `EXC:`
with the stack, and the output before it is kept.

| Function | Does |
|---|---|
| `Ws-LoggedOn`, `Ws-Server`, `Ws-Ensure [user] [server] [-First]`, `Ws-Logon [user] [server] [-First]` | log-on state; address of the connected server; start WorkStation and log on (used by `ebo.sh logon` / `firstlogon`, which supply the password file). `Ws-Ensure` logs off first when another server is connected |
| `Ws-Select '/Server 1/X'`, `Ws-Refresh` | select a System Tree item (expands parents), `F5` |
| `Ws-New parent 'Function Block Program' name` | New Object dialog: filter, pick type, name, Create (about 6 s) |
| `Ws-Delete path` | Delete key, answers `Confirm Delete` |
| `Ws-Export path file [mode]` | context menu `Export...`, preview, Save As, result (about 15 s). mode `Standard` (default), `Special` (keeps every binding) or `Library` |
| `Web-Station [path]`, `Web-Logon` | WebStation in an Edge window of its own, logged on |
| `Ws-Import parent file` | `File > Import...`, file dialog, preview, Import, Close (about 7 s). Throws the preview's messages when it counts an error |
| `Fbe-Open path` | `Ctrl+E` and wait for the editor window (about 17 s) |
| `Fbe-Import $p file`, `Fbe-Save $p`, `Fbe-Exit $p` | editor File menu by command id; Save waits out "Generating application..." (about 5 s) and throws the editor's message on a compile error |
| `Fb-Load parent name file [type]` | create if missing, open, import, save, exit. type `SpaceLogic Function Block Program` for a program in an MP-C / RP-C |
| `Fb-Check file` | compiler message for a program file from the editor started alone, or `compiles` |
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

`Program.hfb(name, module)` (hierarchical block with its own diagram: `inp`, `out`, `o`, and the same calls
inside), `Program.check()` (open inputs and binary / analog mix-ups, HFBs included: run it before every load,
the server only says "compilation failed"), `Program.block(type, name, params, unit, public, module, rw, backup)`, `Program.const(name, value, unit, public,
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
  separate thing: a block inside an HFB still carries `Module\Name`. **Generated by `aut.py` since 2026-11-22**
  (`p.hfb(name, module)`, `inp`, `out`, `o`): a nested HFB used twice compiled and ran on EBO 7.1, and the
  editor draws the wires onto the pins. How the editor draws an HFB: 12 cells wide; height 3 N + 7 cells for
  N = the larger pin count, made even; the pins of one side floor((H - 2) / (n - 1)) cells apart, centred
  (seen right for 4, 10, 12 and 16 pins; **a side with exactly two pins has them at rows 2 and H - 2**, seen on
  heights 14 and 20 on 2026-11-22: until then every wire to such a pin ended in a short slanted piece; three pins
  on a side not seen);
  HFAI / HFDI / HFAO / HFDO are 8 x 4 with the pin at row 2.
- **Expression pins are sorted alphabetically without regard to case** (`a, B, C, D, e`), seen on a 446-block
  program where only that order gives every pin a source of the right kind. `aut.py` follows it.
- **HFB pins outside follow the block ids of the inner HFAI / HFDI (inputs) and HFAO / HFDO (outputs)**, not
  their position on the sheet.
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
  Structure (2026-11-24): code = prefix << 24 | category id << 16 | unit id, ids from `Enterprise
  Server\definitions\system\units\*.xml` (120 categories): Temperature 40 (°C 1, K 2, °F 3), Percentage 32 (% 1,
  ppm 2), Humidity 23 (% Rh 1, so `0x170001` is % Rh), Voltage 50 (V 1, `0x320001`); prefix `0xfd` = milli, so mV
  = `0xfd320001`, ms = `0xfd2e0007` (used in the type definitions). No dBm unit. On a server value: `Unit` attribute
  of the Value PI (hex digits upper case in the export).
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
  `TVP0000n` time-value pairs (Hour, Minute, Value; `Null="1"` ends an entry). Written by
  `objects.py` `schedule(where, name, {"mon-fri": [("06:30", "18:30")], "sat-sun": [("09:00", "15:00")]})`
  (2026-11-22): imports in 7 s, a Special export gives the same children back, and opening the schedule in
  WorkStation shows the week as written (On blocks on the right days and hours). A minute of 0 is left out, as in
  the production exports. Bind a program input to the schedule's `Value`.
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
  and domain files, and the server version in a file name (`3.2.2.61.serverrevision`). A backup holds the user
  database, so treat it as a secret. **Programs and graphics come out with `ebox.py xbk backup.xbk outdir
  [name]`**: the text is not in the database but in zip members `UDT/pu/udt/<a>/<b>___AutFile.cdata` (plain
  gzip of the `.aut`; graphics `___FILE.cdata`), named after the object's type `udt.<a>.<b>`; the object path
  for a type comes from table `ObjectInstance (Id, ParentId, TypeName, NAME)`. Further tables, read by hand
  once: `ConfiguredVariableValue` (current values per module object: the setpoints as the operators left
  them, which differ from the start values in the text), `ForcedVariables`, `BindingEntry` (SubjectId,
  SubjectPropertyId, TargetId, TargetProperty: the subject reads from the target). A program of another
  server shows in a database only as a `system.placeholder.NetworkObject`.
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

## Dashboards from a file (works, 2026-11-22)

A dashboard is shown by WebStation only; WorkStation lists its settings. Everything below was written by
`objects.py`, loaded with `Ws-Import` and seen live in WebStation.

- `client.dashboard.Dashboard` (ShowTime, BackgroundColor, MinColumnSize 250, Margin, Gap) holds one hidden
  child `client.dashboard.DashboardWidget` per tile: InitialAddress -> the object shown, ColumnSpan, RowSpan,
  Order. **A tile shows any object that has a view**: a widget, a graphic, a trend chart. So a tile of one's
  own design is simply a graphic from `tgml.py`; there is no way to add a new widget type.
- Widgets are ordinary objects beside the dashboard (type `client.dashboard.widgets.<X>`), each usable on
  several dashboards:
  `PointGaugeWidget` DisplaySignal -> signal, Min, Max, UseNeedle, hidden children `GuideProperties` (Value,
  Color) for marks on the scale;
  `PointValueWidget` with hidden children `PointGuideSeriesProperties` (DisplaySignal, WidgetIcon 0 none,
  1 CO2, 2 cooling, 3 electricity, 4 heating, 5 temperature, 6 water, 7 lights, 8 blinds);
  `PeriodChartWidget` Period, with children `ChartSeriesProperties` (DisplayLog -> trend log, ChartType 0 bar,
  1 area, 2 curve, 3 line, CalculationMethod 1 max, 2 min, 3 average, 4 sum, 5 delta, 6 meter consumption);
  `LogGaugeWidget` DisplayLog, Period, CalculationMethod, Min, Max;
  `AlarmCountWidget` (needs nothing).
  Period: 0 today, 1 this week, 2 this month, 3 this year, 17 last hour, 7 last 24 hours, 8 last 7 days,
  9 last 30 days, 10 last 12 months. A colour is a signed 32-bit ARGB number (`-65536` = red).
- `objects.py`: `gauge`, `point_values`, `period_chart`, `log_gauge`, `alarm_count`, `dashboard(where, name,
  [(widget or path, columns, rows), ...])`.
- **Every object type with its properties is described in the server's own files**:
  `...\Enterprise Server\definitions\<area>\...\<Type>.xml` (`ObjectType Name=, Base=`, then `Parameter`,
  `ObjectReference`, `PropertyReference` and `Table` entries with type, default and the enumerations). A
  `Table` of type T means hidden child objects of type T. That is the way to find what a type not listed here
  takes; the guess made from these files was accepted at the first import. Areas there include alarm, trend,
  schedule, client (dashboards, panels), notification, report, modbus, bacnet, opcua, webservice, iot.

## WebStation by script (2026-11-22)

- `Web-Station '/Server 1/Folder/Object'` opens `https://localhost/#/Server%201/...` in an Edge window of its
  own (`msedge --app=`: no tabs, no address bar). The server's certificate is not issued for `localhost`, so
  Edge shows "Your connection isn't private": for localhost only, the function goes on through
  Advanced > Continue.
- `Web-Logon` (this copy has no verb for it: log on to WebStation by hand in the window `Web-Station` opens) fills the log-on form (`txtUserID`, `txtPassWord`, button `login`,
  all reachable through UI Automation) with the password set straight into the field, and answers Edge's
  offer to keep the password with "Not now".
- Seen 2026-11-22: `Web-Station '<path>'` straight after `weblogon` came up as an empty dark page (dashboard and
  graphic alike, also after a minute), and a stale Edge gave the same for the root. What worked: stop every
  `msedge` process, `Web-Station ''`, `ebo.sh weblogon`, then click through the list in the page (`Click` on
  the folder row, then on the object). Why the deep link fails in a new window is not known.
- The WebStation window is set topmost by `Web-Station`: while it is open the WorkStation driver fails (seen
  2026-11-22: `Ws-Delete` reports "not there", `Ws-New` "New Object dialog did not open"). Close it before any
  WorkStation step: `Get-Process msedge | ? { $_.MainWindowTitle -match 'Building Operation' } | % {
  [void]$_.CloseMainWindow() }`. `examples/ahu01/deploy.sh` does.
- In PowerShell a variable `$a` is the same as `$A`: a script line that assigns `$a` destroys the driver's
  `$A` (AutomationElement) for the rest of that call. Do not use `$a`, `$ct`, `$ts` as names in `ebo.sh run`.

## Movement and components of one's own (works, 2026-11-22)

Read from the 846 components and 31 snippets shipped with the Graphics Editor
(`C:\ProgramData\Schneider Electric EcoStruxure\Building Operation 7.1\Graphics Editor\Components` and
`Snippets`), then tried with `tgml.py` in a graphic bound to a running pump signal.

- **A component is TGML, not SVG**: a file `Name.tgmlcomponent` whose root is `<Component ContentWidth=
  ContentHeight= Width= Height= Name=>` holding the same elements as a graphic, `<Expose ExposedAttribute=
  Name=/>` for what the user of the component may set, `<Metadata Name="Name" Value=/>` and `Description`. A
  `.png` of the same name beside it is the picture in the Components pane. A component placed in a graphic is
  the same `<Component>` element with `Left` and `Top`; Width / Height against ContentWidth / ContentHeight
  scale it. A snippet (`.tgmlsnippet`, root `<Snippet>`) is a piece of behaviour to drop on an element.
- **`<Path PathData="M.. L.. C.. Z">` takes the same path letters as an SVG path**, so a drawing made as SVG
  carries over shape by shape: `Graphic.from_svg(file)` reads path, rect, circle, ellipse, line, polygon and
  polyline with their fill and stroke (no transforms, gradients or text), and `place()` puts the result into
  a graphic, `save_component()` writes it as a component file.
- **Movement = an `<Animate>` inside the thing that moves**, started and stopped by a bind on its `Animation`
  attribute:
  `<Animate Animation="Stop" Attribute=.. From=.. To=.. Duration="seconds" CalcMode="Linear"><Bind
  Attribute="Animation" Name="X"><ConvertValue AttributeValue="Stop" SignalLessOrEqualTo="0"/><ConvertValue
  AttributeValue="Start" SignalMoreOrEqualTo="1"/></Bind></Animate>`. It repeats while started.
  - turning: wrap it in `<Rotate>` (Attribute `Angle`, 0 to 360) as a child of a Component; it turns around the
    component's middle (`fan()`, `place(..., spin=)`). A static `<Rotate Angle= Center=/>` just tilts.
  - running marks on a pipe: `<Translate>` with Attribute `X` or `Y` on a group of marks, inside a
    `<Component Clip="True">` as long as the pipe; moving by one mark spacing and repeating looks endless
    (`flow()`).
  - blinking: Attribute `Visibility`, `CalcMode="Discrete"`, From `Visible` To `Hidden`, Duration 1
    (`alarm_lamp()`).
  - also in the library: `<Sequence Interval=..>` on a group shows its members one after another as frames;
    Attribute `Fill` / `Stroke` / `ScaleX` / `Opacity` for colour and size transitions; a script can start any
    animation with `setAttribute("Animation", "Start")`.
- **Info box on click** (`info(x, y, title, text)`): a component holding the mark and a hidden `<Group
  Name="pop" Visibility="Hidden">`; its script toggles the group
  (`evt.getCurrentTarget().getChild("pop").setAttribute("Visibility", ...)`). With `Clip="False"` the box may
  reach outside the component; it must come last in the file to lie on top (`tgml.py` keeps such items in
  `Graphic.top`). Tried in WorkStation.
- The shipped components keep their logic in shared functions (`_setAnalogueFans(evt)` ...) that a graphic gets
  with `UseGlobalScripts="True"` and the snippet "GlobalScripts"; what `tgml.py` writes needs none of that.

## More compiler and import rules (2026-11-22, from building a 360-block program)

- **A public constant may be written in one place only** ("Public constant used more than once: X"). The same
  constant as parameter of two blocks, or twice in one block, fails. `aut.py` writes such a constant as
  private (value kept, no longer a property of the program) and says so at `save()`.
- **The real compiler message comes from the editor started alone**: `Fb-Check 'C:\...\X.aut'` (driver) opens the
  file there, runs `Options > Simulate` and returns the message, or `compiles`. A save to the server only says
  "Compilation of program failed". Run it before every `Fb-Load` of a new program.
- **"Failed to parse Menta application. Code error. Row .. Col .." at a save** came from a stale editor: a load
  that failed had left its editor open, and the next load of a program with the same name (after the object
  had been deleted and made again) attached to that window. `Fb-Load` now closes any editor with the
  program's name before it starts and after a failure. The file was never at fault.
- Things that turned out to compile and run: constant names as parameters of PIDA, PIDP, PRCNT, HYST, RAMP;
  feedback loops through several blocks; ACCUM, SHR, DELI, the clock blocks; HFBs with 16 pins; a pin named
  like a block inside.
- **An export rewritten by a program must keep the embedded files in CDATA sections**: without them the import
  ends with "Import failed to commit changeset ... Function_Block_Plugin ... Empty binary file" (the preview
  shows 0 errors). `ebox.py bind` puts them back. The details of a failed import are behind "Copy to
  clipboard" in the result dialog.
- The public signal of an ALARM block is the alarm object's state, not a 0 / 1: 0 normal, 1 alarm, 2
  acknowledged, 3 reset (cause gone, not acknowledged), 4 disabled, 5 fault (`alarm\pt\AlarmState.xml`). A lamp
  bound to it with "1 or more = on" stays lit after the cause is gone: `tgml.py alarm_state()` shows the states.
- Programs start with every input at 0 until its binding delivers: latches for "contact open = alarm" trip in
  that moment (fire, stop, pump feedback) and need one reset after the first load.

## A controller without the hardware: SpaceLogic MP-C / RP-C (works, 2026-11-22)

- An automation server (AS-P, AS-B) cannot be added without a connection: `Servers > New > Server` is a link
  to a running server and asks for its address and log-on.
- **A BACnet/IP controller can**: New `BACnet Interface` on the server, then under its `IP Network` New >
  `SpaceLogic Series` > `MP-C-15A / 18A / 18B / 24A / 36A`, `MP-V-7A / 9A`, `RP-C-12A/B/C`, `RP-C-16A/B/C`,
  `RP-V-4A / 5A`, `IP-IO-DI10 / UIO10 / UIO5DOFA4` (`Ws-New '<...>/IP Network' 'MP-C-36A' 'Name'`). The device
  is created with `Application`, `IO Resources/Onboard IO` (MP-C-36A: `Ub 1` ... `Ub 20` universal inputs,
  `Uc 1` ... `Uc 8` universal inputs / outputs, `DO 1` ... `DO 8`), `Modbus`, `Sensor Bus`.
- **Its program is a `SpaceLogic Function Block Program`** in the Application, edited by the same editor:
  `Fb-Load '<device>/Application' 'AHU' file.aut 'SpaceLogic Function Block Program'`. The full 360-block
  program with HFBs and 33 ALARM blocks was accepted. On save the editor reports "Save successful.
  Downloading to device... Download failed, device is offline": the program is stored on the server and goes
  to the device when it is connected. Type in an export: `bacnet.mpx.program.fb.Program`, modules
  `bacnet.mpx.program.fb.Module`, alarm blocks `bacnet.mpx.program.fb.Alarm`.
- **I/O points are plain objects, so they come from a file** (`objects.py obj()`), imported below
  `<device>/Application`: `bacnet.mpx.point.TemperatureInput`, `VoltageInput`, `CurrentInput`,
  `ResistiveInput`, `DigitalInput`, `CounterInput`, `VoltageOutput`, `CurrentOutput`, `DigitalOutput`,
  `DigitalPulsedOutput`, `TristateOutput`, `PulseWidthOutput` (definitions in `definitions\bacnet\mpx\point`).
  Properties: `Terminal` -> the terminal object (`../../IO Resources/Onboard IO/Ub 3`, a reference without
  property), scaling `ElecBottomOfScale / ElecTopOfScale / EngBottomOfScale / EngTopOfScale`, `Polarity`,
  `ThermistorType`, `DigitalFilter`, `Offset`. The BACnet object number (`ForeignAddress`,
  `<analog-input, 10>`) is given by the server when the file leaves it out. Values that arrive over the
  network are `server.point.AV / BV` in the same Application.
- **Bindings**: a program input reads the point (`AHU/Inputs . TE1 <- ../../TE1 . Value`, written with `ebox.py
  bind` on an export of the program, then delete and import). An output point takes its value from the
  program's output block, and only from an output block; a private RO / BO is addressed by the GUID the
  editor gave it at the save: `TV1_Ctrl . Value <- ../AHU/Outputs . 48551C47-...`. The GUIDs are in the program
  text of an export and survive delete-and-import of the program, not a new save. A reference from an output
  point to a computed public signal is dropped at import without a message.
- Worked through for a whole unit, by script: `examples/ahu01/deploy_mpc.sh` (device, program, 39 points, 73
  bindings, read back from an export; about 5 minutes).
- Not possible to check without the device: download, the live values, the alarms.

## Step chain (start / stop sequence) in a Function Block program (works, 2026-11-26)

Worked example: `examples/fan-sequence` (fan + shut-off damper, 5 steps, supervision, sequence alarm, trip,
a steps list on the graphic, four tests by MQTT). Enterprise Server only, field simulated in the program.

- **The chain is expressions closed through one-cycle delays.** `DELI` holds last cycle's step, `DELR` the timers,
  `DELB` the latches; every cycle computes the new step, step time, settle time and check pointer from those. One
  XPI does the step: `t?0:(A=0?(p&!q?1:0):(r?4:(s?(A=5?0:A+1):A)))` (t trip, A step, p demand, q alarm held, r jump
  to the first stop step, s step finished). The timers restart when the step changes (`Step <> Prev_Step`,
  `Prev_Step` being the `DELI`). A step's requirement count, settle and supervision time come from one nested
  expression per quantity on the step (`N_Req`, `T_Settle`, `T_Max`).
- **Requirement pointer (`RQ_AT`)**: one requirement forward per cycle while met, back at once to the first one not
  met; the step is finished when every requirement has held for its settle time. The supervision timer runs while
  a requirement is not met (in the run step it restarts when all are met again); at `T_Max` the alarm latches the
  step and the first requirement not met (`AL_Step`, `AL_Req`).
- **Expression rules met on the way** (on top of "The .aut format"): at most 8 inputs and 60 characters per
  expression; input letters in sort order, capitals first (`A B ... p q r`), else the pins are wired in a
  different order than meant (`aut.py` refuses such an expression).
- **Trip**: drop the commands in the command expressions themselves (`Fan_Cmd = !Trip & ...`), not through the
  chain: the chain reaches step 0 one cycle later.
- **An alarm object per step and requirement**: an ALARM block on `Seq_Alarm & AL_Step=k & AL_Req=j` (priority 2)
  per pair, one on the trip (priority 1); the server makes alarm objects `<program>/Alarms/Seq_S<k>_R<j>` whose text
  names the step and the requirement. **No single quote in the alarm text**: the .aut string is in single quotes,
  one inside ends it, and the alarm object comes with an empty text without any message (`aut.py` refuses it now).
  The same in a block's description or unit ("rank of today's hour"): there the check (`Fb-Check`) stops with
  the line number of that block. `aut.py` refuses a single quote in a name, unit, description or alarm text.
- **Seeing the alarms**: an **Alarm View** object (`Ws-New '<folder>' 'Alarm View' 'AlarmList'`, opened with
  `Ws-Open`) is a live alarm list; its Quick filter (top of the view) narrows it to one folder's sources. Window >
  Alarms was ticked on this machine but showed no pane.
- **Test by MQTT** (`examples/fan-sequence/run_tests.sh`, `seqtest.ps1`): commands go in through the MQTT client's
  subscription (`{"pointId":"/Server 1/<folder>/Cmd/<name>/Value","value":v}` on one topic, `mosquitto_pub -f` with
  the message in a file), the program's signals come out through data groups, `mosquitto_sub -F "%I %t %p"` writes
  them with their time. `%U` (sub-second time) is refused on Windows ("not supported"): the trace has whole
  seconds. With a Finnish (decimal comma) locale `Get-Date -UFormat %s` gives a comma: use
  `[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()`.
- **Do not name a variable `$a`, `$ts` or `$ct` in code that calls the driver**: PowerShell names ignore case, and
  `lib.ps1` keeps the UI Automation classes in `$A`, `$TS`, `$CT`. A loop variable `$a` hid `$A` from every driver
  function called in the loop, which then failed with "You cannot call a method on a null-valued expression".
- A `mosquitto_sub` left running by a broken run keeps writing into the same trace file (NUL bytes, doubled
  lines): stop any left over before a new trace.
- **WorkStation logs off after 5 idle minutes**, and a new log-on closes the open tabs: log on and open the graphic
  right before each test. The graphic follows the program about 1 s behind.
- **Graphic helpers in `tgml.py`** for this kind of panel: `text_by` (text and colour by an integer state),
  `rect_by` / `circle_by` / `fill_by` (fill by an integer state), `button` (writes on click, no dialog:
  `setValue(b.getFullBindName(), v)` in the script), `set_button` (one per choice, filled while chosen) and `toggle`.
- `alarm_lamp()` (blinking) never showed lit in a screenshot: the capture tends to land in the hidden half of the
  blink. For a lamp that must show in a picture use `lamp()` with an alarm colour.

## Servers in containers, and more than one server (2026-11-23)

Schneider publishes the EBO servers as Linux container images: repository
`github.com/SchneiderElectricBuildings/EBO-Servers`, images `ghcr.io/schneiderelectricbuildings/ebo-enterprise-server`,
`ebo-edge-server` and `ebo-enterprise-central`, one tag per EBO build (see Versions below; linux/amd64 only). WorkStation and the editors stay Windows programs: the container replaces the server half only, and
WorkStation must be the same build as the server (7.1.1.132 here).

- **Licence and EULA come first, and they are the user's business, not the agent's.** The images are Schneider's
  and, by their README, subject to commercial licensing; activated licences are required. The server starts only
  with `NSP_ACCEPT_EULA=Yes`, which is accepting Schneider's end user licence agreement: read it, tell the user
  what it says, and start a container with that setting only when the user has said yes. With `No` the container
  exits with "EULA must be accepted before the server can start". A server without activated licences says so
  itself (system alarm "Licensing violation", a notice in WorkStation, and `System > LicenseManager`). This skill
  does not deal with licences and nothing in it is a way around them.
- **Versions**: the image tag is the EBO build, so a specific version is chosen in the `docker run` line. Tags in
  the registry on 2026-11-23:
  - Enterprise Server: 6.0.1.93, 6.0.2.112, 6.0.3.112, 7.0.1.71, 7.0.2.348, 7.0.3.142, 7.0.7010.1, 7.0.7010.3,
    7.1.0.10002, 7.1.1.132, 7.1.2.171, 7.1.2.9000, 8.0.1.20, and 18 hotfix tags (`HF-604-CP-10-14000-Consolidation`,
    `HF-712-CP-2-5000-Consolidation` ...).
  - Edge Server: the same builds without 7.1.2.9000, and also 5.0.1.128, 5.0.2.109, 5.0.3.117, 6.0.4.90; 22 hotfix
    tags.
  - The list as it is now (no account needed):
    `T=$(curl -s "https://ghcr.io/token?scope=repository:schneiderelectricbuildings/ebo-edge-server:pull" | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')`,
    then `curl -s -H "Authorization: Bearer $T" "https://ghcr.io/v2/schneiderelectricbuildings/ebo-edge-server/tags/list?n=200"`.
  - WorkStation must be the same build as the server it logs on to, so another server version needs its own
    WorkStation installation. Keep an Edge Server and the Enterprise Server above it on the same build.
  - The database follows the version: use one volume per version (`es-7.1.2-db`), do not point an older image at a
    volume a newer one has opened. A newer image on an older volume means an upgrade (the image has
    `prepare-upgrade` and `get-upgrade-log` in `/opt/sbo/bin`); not tried.
  - A tag can be published again with other content. To stay on exactly what was tested, note the digest
    (`docker images --digests`) and start from `image@sha256:<digest>`, or keep a `docker save` copy.
  - Only 7.1.1.132 was run for these notes; the rest is the tag list.
- **Start** (Docker, published ports; the README's own example uses an ipvlan network, which a server needs when it
  must talk BACnet/IP or Modbus to field devices):
  `docker run -d --name es1 -h es1 --ulimit nofile=8192:8192 --restart unless-stopped -p 80:80 -p 443:443 -p 4444:4444
  -e NSP_ACCEPT_EULA=<the user's answer> --mount source=es1-db,target=/var/sbo
  ghcr.io/schneiderelectricbuildings/ebo-enterprise-server:7.1.1.132`.
  `Server state = ServerRunning` in the log after about 5 s. The database lives in the volume (`/var/sbo`): remove
  the volume and the server is new again. Log: `docker logs <name>`.
- **Weight**: image 1.1 GB; about 130 MB of memory and well under 1 % of a core idle, 140 MB with the AHU01 example
  running; database volume 80 MB.
- **First log-on of a new server** (a container, or a fresh database): user `admin` with the product's default
  password (the same as the user name), the certificate question, then a forced `Change Password` dialog (Old /
  New / Confirm), then `Select default workspace`. `EBO_SERVER=<address> ebo.sh firstlogon` does all of it; the
  new password is the one the user types into the credential box (or `EBO_ADMIN_PASSWORD`). It is pasted, not
  typed: a key that the keyboard layout maps differently would go wrong the same way in both boxes and nobody would
  know the password.
- **Certificate question** for a server reached by address: "issued for a different server's address", and
  "expired or not valid yet" as well when the dates of the two machines do not agree. The driver presses
  `Trust certificate` for that one log-on, never ticks "Always trust", and only for the address named in `EBO_SERVER`.
- **Classic Mode is off for a user who never switched it on** (so on every new server): `Ctrl+E` then opens the
  embedded editor and the pencil button is missing. `Fbe-Open` reads the toggle state of the `ShowClassicMode`
  button and switches it on.
- **Everything else is the same as on the Windows server.** The root is `/Server 1` there too, so paths and
  scripts do not change: `EBO_SERVER=<address> examples/ahu01/deploy.sh` loaded the whole AHU01 set (two programs,
  graphic, trend logs, schedules, dashboard, 165 bindings) unchanged.
- **Two servers, one WorkStation**: the window title is `<server name> - <address> - Building Operation
  WorkStation`. `Ws-Server` reads the address, and `ebo.sh logon` logs off first (`Shift+F4`, no question asked)
  when WorkStation is connected to another server than the one asked for. Plain `ebo.sh logon` means `localhost`.

### Edge Server

- The Edge Server image (`ebo-edge-server`, log line `Type = Edge Server CS`) is the software form of an
  automation server. It **runs alone**: WorkStation logs on to it directly, programs and graphics load as on the
  Enterprise Server, no Enterprise Server is needed. Its tree has `System` only (no `Servers`).
- `System > LicenseManager` is a folder on it; `LicenseStatus` in there holds one object per licensed feature:
  Automation Server, Enterprise Server (the connection to one), Field Devices, Server I/O, BACnet IP, Personal
  Dashboards, SAML Authentication, Meter Management, MQTT Read/Write, Microsoft SQL Server, OPC UA, AVEVA PI
  System, Serial Modbus, BACnet MS/TP, SmartDrivers, SNMP Notifications, TimescaleDB, WebStation, Zoning Tool.
  So field buses and protocols are licensed one by one: check there before planning a test with devices.
- `/opt/sbo/firmware` in the image holds Zigbee firmware only: firmware for field controllers has to come from
  elsewhere. Not tried: field devices of any kind, BACnet/IP, Modbus, firmware updates.

### An Edge Server below an Enterprise Server

- **Attach**: log on to the Enterprise Server, select `Servers`, `Ctrl+N` (the only type offered is Server), name,
  `Create`; next page Address / Protocol `https` / Port 443 / Username / Password of the lower server; `Next`
  shows an optional "Create Server from a Backup Set" page; `Create`. The lower server keeps its content, takes
  the new name (its log: `/Server 1 -> /Edge1`) and appears as `/Server 1/Servers/Edge1/...`. Done with
  `ebo.sh run` steps so far, there is no driver function for it.
- **The same name twice in the tree**: `Servers/Edge1/AHU01` now comes before `AHU01`. The driver's tree lookup
  matches direct children only, so `/Server 1/AHU01` is the Enterprise Server's own folder. (It used to take the
  first descendant of that name and exported the wrong object without any error.)
- **Bindings across servers, the rule: bind on the side of the lower server.**
  - Down (the lower server uses a value of the Enterprise Server): an input on the lower server bound to the
    Enterprise Server's value, written as the **absolute path** (`Object="/Server 1/AHU01/SIM/PLANT"`). A relative
    path that climbs above the lower server's root is dropped at import (its log: "A reference pointing above
    server root?") and the point reads 0 with no error on screen. `ebox.py bind` writes the absolute form when the
    target lies outside the place of import. Seen live: a change on the Enterprise Server reached the lower
    server's program input within seconds.
  - Up (the Enterprise Server uses a value of the lower server): **do not let the Enterprise Server read it.**
    A program input or a server value on the Enterprise Server bound to a signal of the lower server read 0, with
    the binding shown as made and no error (cause not found; the capture showed the lower server never opening a
    connection of its own, and the two machines' clocks were months apart). What works: plain value points on the
    Enterprise Server (`objects.py value()` without a source: BV for commands, AV for control signals), the lower
    server's program **output blocks** (`RO` / `BO`, shown as `<tag>_OUT`) bound to those points' `Value` with
    `Ws-Bind`, and the Enterprise Server's logic reading the points. The values then follow at once.
  - Proven with the AHU01 example split in two: plant simulation on the Enterprise Server, controller and graphic
    on the Edge Server (its own SIM program deleted). After Reset the unit ran in closed loop across the servers.
  - Deleting and re-importing a folder on one server leaves the other server's references to it dead (its log:
    `No Driver Module for Path ... of type system.NullType`): bind those again (`Ws-Bind`, in place).
- **Reading values by eye**: open the program, `Variables` tab, expand the module, then `Inputs` / `Outputs`:
  live values with units. The Graphics Viewer tab of a program is not a reliable reading.
- Server log of a Windows Enterprise Server: `...\Building Operation 7.1\Enterprise Server\db\logs\trace.log`.

### A real field controller on a container server (SpaceLogic RP-C, 2026-11-23)

Done with an RP-C-16A on the same network as the machine that runs the Enterprise Server container.

- **No ARM, so no Raspberry Pi**: every tag of the server images is `linux/amd64` only. Hardware for an Edge
  Server container is a small x86 machine.
- **The container needs the network itself for BACnet/IP.** With published TCP ports only (`-p 443:443` ...) the
  server hears no broadcasts and finds no devices. Start it with `--network host` (or on an ipvlan network as in
  Schneider's README) instead of `-p`; it still serves 80 / 443 / 4444. Then
  `Ws-New '/Server 1' 'BACnet Interface' 'BACnet'`; the log says `IP Network opened network #1 at <address>:47808`.
  With host networking only one server container can run on that machine's address.
- **A controller that was hosted by another server does not answer**: ping only, no Who-Is, no ReadProperty, no
  TCP port; it broadcasts a Who-Is for its former server's device instance every 30 s and Device Discovery does
  not list it. After its reset button it shows up under **ID initialization required**.
- **Hosting it**, on the server root, tab `Device Discovery`, type `BACnet devices`, binoculars = Discover all:
  1. right-click the row, `Initialize ID`, dialog `Assign device ID` (a free BACnet device instance): the row
     gets a name, model, firmware version, and `Not hosted`;
  2. make the device object: `Ws-New '/Server 1/BACnet/IP Network' 'RP-C-16A' 'Name'`;
  3. **drag** the discovered row onto that object in the System Tree. `Progress` lists Add IP Address to
     whitelist, Associate with device, Download, Upload. No menu command does this and the object's ID and
     serial fields cannot be typed.
- **Drag by script**: `Drag x1 y1 x2 y2` in `lib.ps1`. Moving the pointer with SetCursorPos while the button is
  down only selects the row; WPF starts a drag on real mouse-move input (absolute `mouse_event`). Expand the
  tree to the target first (`Ws-TreeItem '<path>'`): the Device Discovery view shows the tree collapsed.
- **`Ui-Click` on an element whose rectangle is empty clicks at 0,0** and opens the window's system menu: look at
  `Ui-Center` first, or click by position.
- **Programs**: `Fb-Load '<device>/Application' 'Name' file.aut 'SpaceLogic Function Block Program'`; the save
  downloads to the controller. Seen running in the device: `Executed by` = BACnet device, Status Running,
  `Number of cycles` counting. A blue arrow on an object in the tree means it still has to go to the device
  (`Device > Download ...`) or come from it (`Upload ...`). With a live device `Fbe-Save` can end with "after
  Save the foreground window is ''" although save and download went through (the wait at the end is too short).
- **Firmware**: a controller on much older firmware than the server (2.00 under a 7.1 server) was hosted and ran
  a small program; the server raised "Failure upgrading database download" on it. `Device > Upgrade firmware >
  Select device firmware` opens `Select Firmware`: a list (empty until a package is added), `Browse` for a file on
  the WorkStation machine, Download firmware (optimized / force), Compress, Show upgrade status, activation
  Manually / Immediately / at a time. The server does not fetch firmware by itself, with or without internet, and
  the images carry Zigbee firmware only: the controller firmware package comes from Schneider (partner software
  centre, account needed). Read its release notes for the allowed upgrade path first. Not done here: the upgrade
  itself, physical inputs and outputs.

### Modbus RTU on a SpaceLogic controller: device, register points, bindings (basics, 2026-11-23)

Seen on an RP-C-16A object under a 7.1 server. Made on a controller object that is not tied to hardware, so
creating and exporting are proven, live values are not.

- **Where**: `<controller>/IO Resources/Modbus` (type `bacnet.mpx.modbus.network.Modbus`). Serial only: Framing
  mode `RTU` (fixed), Baud rate, Parity, Stop bits, poll intervals in its properties. `IO Resources/Ports` lists
  the RS-485 ports and USB; there is no Modbus TCP on the controller (Modbus TCP devices go under a server).
- **Firmware**: a controller on old firmware (2.00) refuses the device at the commit with "Unsupported object
  type - structured-view" in the `Create New Object` log: the Modbus object needs newer controller firmware.
  Changing the Modbus object itself is refused the same way ("Unknown property '.../Modbus/BaudRate'"), and
  its blue arrow never clears.
- **Port**: the Modbus object's `Port reference` is empty at first; `...` opens "Choose an available port" with
  the controller's RS-485 ports. Set it, and Baud rate / Parity / Stop bits to match the devices.
- **Device**: `Ws-New '<controller>/IO Resources/Modbus' 'Modbus Device' 'Name'` (type
  `bacnet.mpx.modbus.MasterDevice`). Properties: `Device address` (the slave address, empty at first), `Poll
  register` and `Poll code` (what is read to decide the device is online), `Device identification`.
- **Points**, New below the device: `Modbus Analog Input Point`, `Modbus Digital Input Point`, `Modbus Integer
  Input Point`, `Modbus Multistate Input Point`, the same four as `... Output Point`, and `Modbus Point Group`
  (`Ws-New '<device>' 'Modbus Analog Input Point' 'Name'`, about 14 s each). Types in an export:
  `bacnet.mpx.modbus.point.AnalogInput`, `AnalogOutput`, `BinaryInput`, `BinaryOutput`, `IntegerOutput` ...
  Each is also a BACnet object of the controller (`ForeignAddress` `<analog-input, 11>`), numbered by the server.
- **Register settings** are on the point's Basic page under `Modbus Settings`: `Register number`, `Register
  type` (16 bit unsigned by default; pick the 32-bit / float form and word order the device uses), `Bit mask`
  for bits out of a register. Inputs are read, outputs are written.
- **Bindings**: as for the controller's own I/O points. A program input reads the point's `Value`
  (`Program/Inputs . X <- ../../<path to point> . Value`); an output point takes its value from a program
  **output block** (`<tag>_OUT`), bound with `Ws-Bind` or with `ebox.py bind` on an export. Bind again after a
  reload of the program.
- **After changes**: a blue arrow on the device or a point means it has not gone to the controller yet
  (`Device > Download ...`).

### A third-party BACnet/IP device on a server (2026-11-23)

- Device Discovery (server root tab, type `BACnet devices`, binoculars = Discover all) lists it, also a device
  behind a BACnet router (shown under `Network_1/<gateway>/Network_<n>`). The server and the device must be in
  one broadcast domain when the device has no BBMD; a firewall between them has to pass UDP 47808 both ways,
  the device's answers arrive as new flows.
- **Host it**: drag the discovered row onto `<server>/BACnet/IP Network` (`Drag`). A box says "Upload is
  required to host objects in device."; after OK the device is there as `bacnet.DeviceProxy` with an empty
  `Application`.
- **Bring its objects in**: right-click the device, `Device > Upload all objects`, `Progress` ... Done. The
  device's objects appear under `Application` with the device's own names, analog inputs as
  `bacnet.pointproxy.analog.Input` ("BACnet Analog Input (Generic)") with value, unit and status flags.
- Use them like any value: bind `<device>/Application/<object>` . `Value` into a program input, a graphic or a
  trend log. A device without COV is polled.
- The toolbar of the Device Discovery tab sits a few pixels differently from one server to the next (the
  binoculars were at x 500 on one, 516 on another): take a screenshot before clicking by position.

### Graphics: boxes with live content, colour by value (2026-11-23)

- `Graphic.popup(x, y, w, h, draw, side, mark)`: a round mark; a click opens a box whose content is drawn by
  `draw(p, ox, oy)` with everything a Graphic can draw (values, lamps, bars), a second click closes it. Same
  form as `info()` (a Component with a hidden Group and an OnMouseClick script). Binds inside a hidden Group
  keep running, and one bind name may stand in several places of a page.
- `Graphic.thermometer(x, y, name, lo, hi)`: fill colour and column height set by a script from the value, a
  straight-line blend cold - mid - hot (`setAttribute("Fill", "#rrggbb")` with a computed colour works).
  `Graphic.level_lamp(x, y, name, limit)`: two colours by a limit on an analog value (`ConvertValue`).
- **Loading a graphic again keeps its bindings** when the bind names are the same (`Gfx-Load` on an existing
  graphic; unlike a program, whose reload drops them). New bind names are simply unbound until `Ws-Bind`.
- `Gfx-Load` failed once while the graphic's own tab was open in WorkStation: `Tab-Close '<name>'` first.
- **Age of a polled value**: a device without COV or time stamps gives no "last updated". A small program with
  `DELR` (value of the cycle before), `TCYC` and an expression counts the seconds since any watched value
  changed (worked example: `examples/room-sensor`, `make_age.py`).
