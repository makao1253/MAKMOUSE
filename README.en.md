# MAKMOUSE CAD Software 1.4.1

*Wersja polska: [README.md](README.md)*

A driver for your own 3D mouse, made for CAD applications (Fusion 360,
SolidCraft, Inventor). It turns the knob, the ring and the side buttons (three
or six — your choice in *Settings*) into full 3D navigation — the SpaceMouse
idea, running on your hardware.

Python + PySide6, everything below the GUI on plain `ctypes` — no pywin32, no
drivers, no external HID libraries.

---

## What is new in 1.4.1

* **Invert zoom** — a new box in *3D navigation → X/Y axes*, next to *Swap X/Y*.
  It reverses the ring's direction: zooming in becomes zooming out, in ordinary
  scrolling and in zoom through the 3D add-in (Fusion, SolidCraft). Like the rest
  of that section, it belongs to the profile.

---

## What is new in 1.4.0

* **Direct control in SolidCraft too.** Next to *Direct control (3D add-in)*
  there is an **Add-in** list: *Fusion 360* or *SolidCraft*. SolidCraft needs no
  separate plug-in — it connects to the MAKMOUSE bridge itself once you turn on
  *Preferences → Navigation → 3D mouse → Navigate with a device app on this
  computer*. The camera moves without the cursor, and your ordinary mouse works
  independently.
* **The axes reach the chosen application only.** Add-ins introduce themselves to
  the bridge, so with Fusion and SolidCraft running at once the knob moves the
  camera only in the application of the active profile.
* **A new factory SolidCraft profile** (`solidcraft.exe`): direct control,
  button 1 = pan, 2 = `Ctrl+Z`, 3 = fit view. An older configuration gets it
  automatically on the first start.
* *Fusion view* is now called **View (3D add-in)** — it works in Fusion and in
  SolidCraft.
* The bridge notices an application closing right away instead of at the next
  send, so the profile falls back to drag emulation sooner.

---

## What is new in 1.3.3

* **Zoom sensitivity is now the zoom step, not the number of impulses.** Still one
  click per ring impulse, but each click carries a different weight: a page scrolls
  by fewer lines and the camera approaches the model by a smaller amount — instead
  of forcing you to turn the ring more times.
* **Orbit and pan sensitivity now work with direct control too.** A button bound to
  *3D navigation* (also as a toggle) gives the axes the sensitivity of its mode,
  independent of the *Sensitivity — knob* slider.
* One zoom slider instead of two — the same step applies to the ring and to the
  *3D navigation → Zoom* action.
* The live preview is back to a **legend below the graphic**; the state of a
  button's function is shown next to it by a **green or red dot**, the same one the
  top bar uses for the device.
* *Direct control (3D add-in)* moved to the bottom of the *X/Y axes* section, with
  the other check boxes.

---

## What is new in 1.3.2

* **Zoom sensitivity (ring) finally works** — the slider used to do nothing to
  ordinary scrolling (the way it works was changed in 1.3.3, see above).
* **The knob moves the cursor without a modifier.** An empty movement gesture no
  longer blocks the axes — outside Fusion you no longer have to enter `Shift`
  just to make anything happen.
* **The *3D navigation* tab is now per profile** (sensitivities, inversions,
  cursor behaviour). The old configuration migrates by itself.
* **New *Leave the cursor where the gesture ended* box** — decides whether the
  pointer stays where it arrived or returns to its previous position.
* **Direct control (3D add-in)** moved to *3D navigation → X/Y axes*, together
  with the add-in status. With direct control on, the *Continuous gestures*
  section disappears instead of being greyed out.
* **A profile switch next to its name** in the list; **a function switch in the
  corner of every button tile**.
* **A choice of 3 or 6 side buttons** in *Settings* — preview and buttons tab
  follow it.
* **An accent colour for the whole application**, ten to choose from.
* **The whole interface is tighter** — tabs fit without scrolling on a smaller
  screen.
* **[build_exe.bat](build_exe.bat)** — builds a ready `.exe` with one click.

---

## Installation and start

```powershell
python -m pip install PySide6-Essentials
python d:\MAKKEY\run.py
```

Without a console window: [MAKMOUSE.bat](MAKMOUSE.bat) or `pythonw run.py`.

A ready-made `.exe` (no Python needed) and moving the project to another
computer: **[INSTALL.md](INSTALL.md)**.

---

## Interface language

*Settings* tab → **Language**: `Polski` and `English`. The choice is stored in
the configuration (`"language": "pl" | "en"`), so the window comes back up in
the same language next time.

Translations are baked into the widgets when they are created, so changing the
language **rebuilds the window from scratch**. The engine, the controller and
the bridge stay alive throughout, so the device never stops working — only the
window disappears and comes back translated.

New texts go into [makmouse/i18n.py](makmouse/i18n.py): the key is the Polish
source string, the value is the translation. A missing entry does not break the
interface — the Polish original shows up instead.

---

## The in-app manual

The round **i** button in the top-right corner opens the full manual — the same
content as below, without leaving the program.

## Light and dark theme

A two-position switch next to the **i** button: **sun** = light theme,
**moon** = dark. It swaps the whole palette on the fly, with no restart, and the
choice is saved in the configuration.

## Accent colour

*Settings* → **Accent colour**: ten basic colours (blue — the factory one, indigo,
violet, pink, red, orange, amber, green, teal, graphite). Deliberately not a full
RGB palette — a short list keeps the interface coherent.

The chosen colour goes through the whole application immediately, with no restart:
switches, selections, sliders, the tab underline, the glowing ring on the graphic,
the tray icon and the highlights in the live preview. The *hover* and *pressed*
shades are derived from it automatically.

## Number of side buttons

*Settings* → **Number of side buttons**: `3 buttons` or `6 buttons`. The choice
immediately switches the *Buttons and gestures* tab (the tiles), the live preview
(the drawing of the band) and the lamps in *Monitor*.

Settings of buttons outside the chosen count **are not lost** — they stay in the
profile and come back when the six-button variant is selected again.

---

## Where the configuration lives

By default `%APPDATA%\MAKMOUSE\config.json`, but on the *Settings* tab →
**Configuration file** you can point to any other path — a USB stick, a project
folder, a cloud-synced directory.

* *Change location…* saves the current settings in the new place and from then
  on everything goes there. The old file is left untouched — nothing is deleted,
  cleaning up is your call.
* *Back to default* restores `%APPDATA%`.

The location itself is remembered in `%APPDATA%\MAKMOUSE\location.json` — the
one file that always stays in APPDATA, because something has to be the starting
point. If the file it points at disappears (an unplugged USB stick, say),
MAKMOUSE starts with default settings and says so, instead of silently
overwriting anything.

*Export / Import* is a different thing: a one-off copy to and from a file,
without changing where settings are saved.

---

## Device recognition

**MAKMOUSE has no device picker.** The application walks every HID collection
visible to Raw Input, reads the manufacturer and product strings from each
(`HidD_GetManufacturerString` / `HidD_GetProductString`) and reacts **only** to
those containing the text `MAKMOUSE`. Every other mouse, keyboard or tablet is
ignored — you cannot accidentally capture somebody else's hardware.

In the firmware it is therefore enough to set the USB descriptor so that
`iProduct` or `iManufacturer` contains `MAKMOUSE`. The name is detected
independently of VID/PID, so you can change those without touching the
application.

The device presents itself as **one collection: Multi-axis Controller**
(`Usage Page 0x01` / `Usage 0x08`) — the same class the original SpaceMouse
works in. Axes, scroll and buttons arrive in a single HID report.

The state is shown by **the coloured dot next to the MAKMOUSE label** in the top
bar: green = device connected and active, red = no device or the *Active* switch
is off. The full state description is on the *Device* tab. Hot-plug is supported
— the list refreshes itself when the device is plugged in.

---

## The graphic = a live preview

The drawing of the device in the middle of the window is a state indicator:

* **side button** — lights up in the accent colour when pressed,
* **knob** — tilts towards the movement and shows a direction arrow,
* **ring** — brightens and shows an arrowhead in the direction of rotation.

Below the drawing is a **legend** with the current binding of each element: the
side buttons, the knob (*Mouse move*) and the ring (*Scroll*). Next to every button
sits a **green or red dot** — exactly the one the top bar uses for the state of the
device. Red means the function of that button is switched off by the box in the
corner of its tile; the assigned action is still spelled out, so you know what
comes back when you switch it on.

The drawing and the legend follow the **3 or 6 buttons** choice in *Settings*.

The *Monitor* tab additionally shows a **Pressed buttons** field: the name of the
button currently held and the highlighted tiles of all of them.

---

## What the device does and what MAKMOUSE adds

All of the hardware fits into a single HID report (5 bytes, Report ID 1):

| offset | field | what it is | name in the application |
|---|---|---|---|
| 0 | Report ID = 1 | — | — |
| 1 | X (`0x30`) | knob, horizontal axis | *Mouse move* |
| 2 | Y (`0x31`) | knob, vertical axis | *Mouse move* |
| 3 | Rz (`0x35`) | ring encoder (20 impulses per turn) | *Scroll* |
| 4 | bits 0–5 | side buttons | *Side button 1–6* |

All button bits are read, but only as many reach the actions as the device has
according to *Settings → Number of side buttons* (3 or 6). The three-button
variant uses bits 0–2, the six-button one adds bits 3–5 of the same byte.

The axes and the encoder are 8-bit signed and **relative** — every report
carries a change, not a position. The factory settings of the application match
that exactly, so nothing needs configuring after plugging in.

MAKMOUSE adds the layer that turns this into CAD gestures.

### Full separation from your ordinary mouse

This is the main advantage of that descriptor. Windows does not interpret the
*Multi-axis Controller* collection, so the device **does not move the cursor,
does not scroll and does not type characters on its own**. The application
controls everything. In practice this means:

* the knob does not take the cursor away from your ordinary mouse — you can work
  with two hands,
* the sensitivity slider works, because it is MAKMOUSE that performs the motion,
* nothing needs to be blocked, and that matters: **returning 1 from a low-level
  hook removes the event from the whole pipeline together with the Raw Input
  report** (measured: key passed through → 6 reports, key blocked → 0). Blocking
  and device recognition are mutually exclusive, so every project built on
  blocking eventually runs into this.

A consequence worth remembering: **without MAKMOUSE running, the device does
nothing.** That is not a fault, it is the price of the separation.

The application does not register any keyboard in Raw Input either, and installs
no keyboard hook — it does not see a single keystroke in the system.

Input sources are installed per mode, not once at startup. In *Raw HID* mode the
application **does not install the `WH_MOUSE_LL` hook and does not register the
Mouse collection** in Raw Input, so ordinary mouse events do not pass through a
single line of MAKMOUSE code. This has a practical meaning: a low-level hook is
called on the thread that installed it, so its mere presence in a Python process
adds latency to every movement of every mouse in the system. The hook only comes
back if you manually switch the mode to *Mouse* (for older firmware).

### Continuous gestures (*Buttons and gestures* tab)

Knob movement and ring rotation have no "release" — the only signal that the
gesture ended is that events stopped arriving. MAKMOUSE therefore holds the
modifier for as long as the movement lasts and lets it go after 250 ms of
silence.

Every axis movement is driven by the *Navigator*: it remembers the pointer
position before the gesture and performs the drag (because that is the only way a
3D application will orbit). What happens to the cursor afterwards is decided by
the **_Leave the cursor where the gesture ended_ box** on the *3D navigation* tab
— on by default, so the pointer ends where it arrived. Turn it off and it returns
to the position from before the gesture (the 1.3.1 behaviour). While a side
button is held, the gesture stays open until you release it.

**A modifier is not required.** An empty movement gesture is a valid setting: the
knob then moves the cursor just like an ordinary mouse. Up to 1.3.1 a missing
modifier blocked the gesture completely and the knob was dead everywhere except
profiles with an orbit chord entered — that is fixed.

* **Mouse move + `Shift` and MMB** → orbit in Fusion 360 / Inventor (this is the
  default setting of both CAD profiles).
* **Mouse move with no modifier** → plain cursor movement.
* **Scroll + `Ctrl`** → stepped zoom; `scroll + H` or any other key works too.

When a profile has **Direct control (3D add-in)** enabled, the whole *Continuous
gestures* section **disappears** from the tab — the axes go to the add-in then and
modifiers have no effect at all.

In the "what to hold" fields (continuous gestures, application gestures, the
*Hold keys/button* action) it is enough to press **the modifier alone** —
`Shift`, `Ctrl`, `Alt`, `Win` or a combination. A main key is not required; if
you add one, it is stored together with the modifiers. Fields that capture full
shortcuts (e.g. *Keyboard shortcut*) still require a main key.

Scroll with a modifier is **intercepted and re-sent** — otherwise it would reach
the application a fraction of a second before the modifier and act as an ordinary
scroll. The block turns on automatically only when the scroll gesture has a
modifier assigned.

### Side buttons

| Action type | Behaviour |
|---|---|
| Nothing | the button goes to the system unchanged |
| 3D navigation | orbit / pan / zoom active for as long as you hold |
| Keyboard shortcut | a pulse on press (e.g. `Ctrl+Z`) |
| Hold keys/button | holds the combination until released |

A pressed side button **disables the movement gesture** — which is what makes the
default layout work like this: movement alone orbits, movement with button 1
(MMB held) pans the view.

Every tile has a **box in its top-right corner**: it switches off the function of
that one button while leaving its settings untouched. A switched-off button goes to
the system unchanged and its dot in the preview legend turns red.

---

## Profiles

Profiles switch by themselves according to the active application (the `.exe`
list in the profile). Seven ship by default: **Fusion 360** (marked as default, so
it also applies everywhere no other profile matches), SolidCraft, Inventor,
Blender, SolidWorks, SketchUp and Rhino. You add your own with *Add* or
*Duplicate*.

**The box next to the name in the list** switches a whole profile on and off,
without opening its settings. A disabled profile is greyed out and takes no part
in matching the active application.

A profile owns its button bindings, continuous gestures, application gestures,
direct control **and the whole X/Y axes section** (since 1.3.2 — sensitivities and
inversions used to be shared by the whole application). A 1.3.1 configuration is
migrated automatically: the existing axis settings become the starting point of
every profile.

---

## Direct control — the Fusion 360 add-in (no cursor involved)

Mouse emulation has a hard limit: for a 3D application to orbit, the cursor
**must** move. That is how every drag-based solution works.

SpaceMouse gets around it differently — its driver does not pretend to be a
mouse, it hands the axes to the application, which computes the camera itself.
MAKMOUSE now does the same for Fusion: an add-in running **inside** the program
moves the camera through the API, so the cursor does not twitch by a single pixel
and you can keep working with an ordinary mouse at the same time.

```
MAKMOUSE (reads HID)  --TCP 127.0.0.1:8765-->  add-in in Fusion  -->  camera
```

**Installation.** The source is in [fusion_addin/MAKMOUSE/](fusion_addin/MAKMOUSE/).
Copy that folder into `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`.
In Fusion: *Utilities → Scripts and Add-Ins → Add-Ins → MAKMOUSE → Run*, plus
*Run on Startup*.

**Behaviour.** A profile with `"direct": true` (Fusion 360 by default) sends the
axes to the add-in. When no add-in is connected, the profile **falls back by
itself** to drag emulation — closing Fusion does not immobilise the knob. A
button with the *3D navigation* action presses nothing with the mouse in this
mode, it only switches the mode inside the add-in (e.g. orbit → pan).

## Direct control — SolidCraft (no add-in to install)

SolidCraft has the bridge built into the program itself, so nothing is installed
in it:

```
MAKMOUSE (reads HID)  --TCP 127.0.0.1:8765-->  SolidCraft  -->  camera
```

1. In SolidCraft: *Preferences → Navigation → 3D mouse →* tick **Navigate with a
   device app on this computer** (port `8765`, the same as `"bridge_port"` in the
   MAKMOUSE configuration). *Connected · MAKMOUSE* appears next to it.
2. In MAKMOUSE the **SolidCraft** profile already has *Direct control* on and
   *SolidCraft* chosen in the **Add-in** list. Do the same for a profile of your own.

The knob orbits (a button with the *3D navigation* action switches it to pan or
zoom), the ring zooms, the *View (3D add-in)* action sets a standard view. While a
sketch is edited the view doesn't turn — the knob pans it then. SolidCraft also
reads 3D mice over HID itself; while MAKMOUSE is connected through the bridge,
SolidCraft leaves the device named *MAKMOUSE* to it, so the view doesn't move
twice. Only the SolidCraft window with focus moves.

Limitation: direct control works in **Fusion and SolidCraft**. Blender, Rhino,
SolidWorks or Creo need their own plug-ins — each has a separate API. The bridge
protocol is shared
though, so an add-in for the next application is mostly a matter of translating
the same three messages into its API: **[ADDONS.md](ADDONS.md)** describes how,
with a concrete plan for Creo Parametric.

An alternative that covers every package at once is emulating a real SpaceMouse
in the firmware (3Dconnexion VID/PID + the 3DxWare driver), which does however
mean using somebody else's vendor identifier.

---

## 3D navigation — the "hold a mode" action

When a side button has the *3D navigation* action, MAKMOUSE synthesises the full
gesture:

1. it remembers the cursor position and (optionally) puts it in the middle of the
   window,
2. it presses the modifiers and the mouse button defined in the profile,
3. it turns the X/Y axes into **absolute** cursor movement, so Windows pointer
   acceleration does not affect the result,
4. at the screen edge it **re-anchors the gesture** (releases the button, returns
   to the centre, presses again) — so you can keep rotating forever,
5. on release it lets everything go and either leaves or restores the cursor —
   depending on the *Leave the cursor where the gesture ended* box.

The same mechanism drives the knob gesture, so the cursor handling applies to
**every** axis movement, not only to an action bound to a button. Two settings —
*Re-anchor the gesture at the screen edge* and *Center the cursor in the window
before the gesture* — apply only to gestures that hold something (orbit, pan).
Plain cursor movement with no modifier skips them, because they would amount to
teleporting the pointer to the middle of the screen.

**The whole *3D navigation* tab belongs to the selected profile** — every
application gets its own chords, sensitivities and cursor behaviour.

Default application gestures — the orbit chord differs between packages and that
is the only thing that really needs changing. Everything is editable in the UI:

| Application | Orbit | Pan | Zoom |
|---|---|---|---|
| Fusion 360 / Inventor | `Shift` + MMB | MMB | wheel |
| Blender | MMB | `Shift` + MMB | wheel |
| SolidWorks | MMB | `Ctrl` + MMB | wheel |
| SketchUp | MMB | `Shift` + MMB | wheel |
| Rhino | RMB | `Shift` + RMB | wheel |

The default (catch-all) profile uses the Fusion chord, because `Shift` + MMB is
the most common one — so the knob also works in an application that does not have
its own profile yet.

### Axis sensitivity

The firmware reports the axes as **relative** (`Relative`): every report carries a
change, not a deflection. The "deflection = speed" variant (as in the original
SpaceMouse) was removed — with this descriptor it had no way to work, and the
*dead zone* and *progression curve*, which served it alone, went with it.

The *Sensitivity — knob* slider scales knob movement itself. The two lower ones
(*orbit*, *pan*) apply while a side button holds a *3D navigation* action — also as
a toggle. Example: button 1 set to *3D navigation → Pan* with the toggle ticked
switches the knob to panning, and from then on the axes use *Sensitivity — pan*,
independent of *Sensitivity — knob*; the next press brings them back.

**All of them work the same in both paths** — through the Fusion add-in and through
drag emulation. (In 1.3.2 the channel to the add-in always used the knob
sensitivity, so orbit and pan had no pace of their own there — that is fixed.)

**Sensitivity — zoom (ring)** is the **step of one click**, values from 0.1 to 5.0
in steps of 0.1. The number of clicks does not change — the ring still gives 20 per
turn — what changes is how far one click moves things:

| value | what one click does |
|---|---|
| 0.3 | three times finer: fewer lines on a page, a closer approach to the model |
| 1.0 (factory) | the same as an ordinary mouse wheel click |
| 2.5 | a two-and-a-half times bigger step |

The same value applies in both places where zooming happens: the ring in an
ordinary application (a scaled `WHEEL_DELTA`, i.e. fewer lines scrolled) and the
camera in a 3D application (a shorter zoom step — through the add-in or through the
*3D navigation → Zoom* action). That is why there is one slider and not a separate
one per path.

> Very low values (0.1–0.2) send a fraction of a standard wheel click. Modern
> applications (browsers, Fusion, Office) accumulate such events correctly; the odd
> legacy application that divides `WHEEL_DELTA` without a remainder may skip them —
> raising the value is then enough.

---

## Side button actions

| Type | What it does |
|---|---|
| Nothing | the button passes through unchanged |
| 3D navigation | orbit / pan / zoom while held |
| Keyboard shortcut | sent once on press |
| Hold keys/button | held until released |
| **View (3D add-in)** | sets the view: front, back, left, right, top, bottom, isometric, fit |

*View (3D add-in)* goes through the bridge to the add-in of the application chosen
in the profile (Fusion or SolidCraft), so it appears **only in a profile with
direct control enabled** — elsewhere it is not on the list, because it would have
no way to work.

### Toggle

Every action that holds something (*3D navigation*, *Hold*) can act as a
**toggle**: the first press turns it on, the second turns it off — releasing the
button extinguishes nothing. The typical use: a button switches the knob from
orbit to panning the model and leaves it that way until the next click.

---

## Read mode

The device presents itself as a *Multi-axis Controller* and reports in the layout
fixed by the firmware (report ID 1, 5 bytes). There is nothing to choose here, so
the *Device* tab now only shows the detected hardware. Windows does not interpret
that collection, so the cursor, scroll and buttons are driven exclusively by
MAKMOUSE.

---

## Troubleshooting

**"MAKMOUSE — Inactive".** The USB descriptor does not contain that name, or the
device is not plugged in. Check `iProduct`/`iManufacturer` in the firmware and
click *Scan again* on the *Device* tab.

**A side button does nothing.** Open *Monitor* and press it. If the raw report
bytes change but there is no "side button N DOWN" line, the firmware is sending a
different report layout than the fixed one (report ID 1, buttons in byte 4). If
nothing changes at all, check that the device is *Active*.

**Movement or scroll goes the wrong way.** *Invert X* / *Invert Y* on the
*3D navigation* tab; for the ring (scroll and zoom) tick *Invert zoom* there.

**Scroll does not zoom in Fusion.** Fusion renders with an **orthographic** camera
by default, in which moving the eye does not change the image — the view scale is
held by `viewExtents`. The add-in detects the camera type and moves the right
field.

**The knob works, but changing sensitivity does nothing in Fusion.** Make sure the
Fusion profile has *Direct control* ticked and that the preview shows
*Add-in connected*.

**It does not work over a window running as administrator.** Low-level hooks will
not capture input going to a process with a higher integrity level. Run MAKMOUSE
as administrator (Fusion 360 and Inventor do not require this).

**Something got stuck.** The panic hotkey (`Ctrl+Alt+F12` by default) releases
every held key and switches MAKMOUSE off.

---

## Project structure

A full description of the code — what every file does, how data flows, the
threads, where to look when changing something — is in
**[STRUKTURA.md](STRUKTURA.md)** (Polish). In short:

```
run.py                  application start + window rebuild on language change
build_exe.bat           builds the ready .exe (single file or folder)
build_installer.bat     builds the MAKMOUSE-<version>-setup.exe installer with one click
MAKMOUSE-onefile.spec   PyInstaller recipe - single file dist\MAKMOUSE.exe
MAKMOUSE.spec           PyInstaller recipe - folder dist\MAKMOUSE\ (for the installer)
Program instalacyjny (exe)/
  MAKMOUSE.iss          Inno Setup script; finished installers land in Output\
makmouse/
  i18n.py               PL/EN translation dictionary and the tr() function
  winapi.py             Win32 structures and prototypes (ctypes)
  devices.py            device enumeration, reading names from the USB descriptor
  engine.py             engine thread: Raw Input + hooks + stream pairing
  output.py             SendInput: keyboard (scancode), buttons, movement, scroll
  navigator.py          X/Y axes -> orbit/pan/zoom gestures, edge re-anchoring
  profiles.py           configuration model, profiles, JSON save/load
  appwatch.py           active application detection
  controller.py         wiring of engine, profiles and actions; continuous gestures
  keys.py               key names <-> virtual codes, shortcut parsing
  ui/
    theme.py            light/dark theme, 10 accent colours, generated assets
    device_view.py      the drawn 3D graphic of the device — live preview
    widgets.py          cards, switches, shortcut capture, indicators
    help_dialog.py      the manual opened with the "i" button
    main_window.py      main window
images/                 reference photos the graphic was drawn from
```

---

## Building the .exe

The easy way: **double-click [build_exe.bat](build_exe.bat)**. The script checks
for Python, installs `PySide6` and `pyinstaller` if they are missing, builds the
program and leaves the finished file at:

```
Program gotowy (bez instalatora)\MAKMOUSE.exe
```

That is **one ~36 MB file** you can copy to a USB stick and run on another
computer without installing anything. Running the script again overwrites the
previous version — nothing to clean up by hand.

There are two variants:

| command | result | notes |
|---|---|---|
| `build_exe.bat` | `Program gotowy (bez instalatora)\MAKMOUSE.exe` | one file, ~3–5 s start (unpacking into a temporary folder) |
| `build_exe.bat folder` | `Program gotowy (bez instalatora)\MAKMOUSE\MAKMOUSE.exe` + `_internal\` | many files, instant start; this is what the installer uses |

By hand, without the script, it is exactly the same as:

```powershell
python -m pip install pyinstaller PySide6
python -m PyInstaller --noconfirm --clean MAKMOUSE-onefile.spec   # single file
python -m PyInstaller --noconfirm --clean MAKMOUSE.spec           # folder variant
```

Both recipes set `console=False` (the application lives in the tray and prints
nothing to stdout), attach the `makmouse.ico` icon and cut out unused Qt modules —
without that the package grows by several hundred megabytes of QtWebEngine and
QtQuick. The `build\` and `dist\` folders are PyInstaller's working output and can
be deleted at any time.

The application is Windows-only (Raw Input, LL hooks, `SendInput`), so the exe has
to be built on Windows and on the same architecture as the target. Moving the
finished package to another computer is described in [INSTALL.md](INSTALL.md).

---

## Version numbering

The version lives in one place — `makmouse/__init__.py` — and travels from there
to the window title, the top bar, the tray and the manual. The `1.x.x` scheme:

* **1.x.0** — a new feature or a change of behaviour,
* **1.x.y** — a fix with no change of behaviour.
