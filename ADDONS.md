# Dodatki do innych programów CAD (Creo, SolidWorks, Rhino, Blender…)

*[English version below](#add-ins-for-other-cad-applications-creo-solidworks-rhino-blender)*

Dodatek do Fusiona nie jest niczym wyjątkowym — to **60 linijek logiki**
opakowanych w API konkretnego programu. Cała trudna część (czytanie HID,
profile, filtrowanie osi) siedzi w MAKMOUSE i jest wspólna. Dodatek robi trzy
rzeczy:

1. łączy się gniazdem TCP z MAKMOUSE,
2. czyta linie JSON i sumuje przyrosty,
3. przekłada je na kamerę **na wątku głównym** programu.

Poniżej: protokół, wzorzec, i co konkretnie zrobić w Creo.

---

## 1. Protokół mostu

MAKMOUSE jest **serwerem** i nasłuchuje na `127.0.0.1:8765` (port zmienny przez
`"bridge_port"` w konfiguracji). Dodatek jest **klientem** i ponawia próby, bo
kolejność uruchamiania programów nie jest niczym gwarantowana.

Format: **jeden obiekt JSON na linię, UTF-8, zakończony `\n`**. Prawie cały ruch
idzie od MAKMOUSE do dodatku; dodatek wysyła najwyżej jedno powitanie.

**Powitania (od 1.4.0).** Zaraz po połączeniu MAKMOUSE wysyła
`{"t":"hello","server":"MAKMOUSE","device":"MAKMOUSE","version":"1.4.0"}`
(`device` to napis z deskryptora USB urządzenia). Dodatek może odpowiedzieć
`{"t":"hello","app":"<program>"}` — MAKMOUSE wysyła wtedy osie tylko temu
dodatkowi, którego program jest wybrany na liście **Dodatek** w profilu
(`"addon"` w konfiguracji). Dodatek, który się nie przedstawi (dodatek Fusiona),
liczy się jako `fusion`. SolidCraft przedstawia się jako `solidcraft`. Nowy
dodatek dla innego programu potrzebuje nowej pozycji w `ADDONS` w
[makmouse/profiles.py](makmouse/profiles.py) i stałej w
[makmouse/bridge.py](makmouse/bridge.py).

| Komunikat | Kiedy | Znaczenie |
|---|---|---|
| `{"t":"axis","x":1.5,"y":-3.0}` | ruch gałki | przyrost osi w jednostkach urządzenia (±127 na raport, już przemnożony przez czułość) |
| `{"t":"zoom","d":1.0}` | obrót pierścienia | kliki enkodera ze znakiem |
| `{"t":"mode","mode":"pan","on":true}` | przycisk boczny z akcją *Nawigacja 3D* | tryb, w jakim mają działać osie: `orbit` \| `pan` \| `zoom` |
| `{"t":"view","name":"iso"}` | przycisk boczny z akcją *Widok* | widok standardowy: `front`, `back`, `left`, `right`, `top`, `bottom`, `iso`, `fit` |

Dwie własności, o których warto pamiętać:

* **osie są przyrostowe** — nie ma pozycji absolutnej, każdy pakiet to „o tyle
  przesuń";
* **pakiety mogą się gubić** przy zatorze (MAKMOUSE wyrzuca najstarsze z kolejki).
  W strumieniu przyrostów to nie szkodzi — świeższe dane są ważniejsze niż komplet.

Podejrzeć strumień można bez żadnego CAD-a:

```powershell
python -c "import socket;s=socket.create_connection(('127.0.0.1',8765));[print(l) for l in s.makefile()]"
```

Rusz gałką — jeśli w konsoli lecą linie JSON, most działa i problem (gdyby był)
leży po stronie dodatku, nie MAKMOUSE. Warunek: profil aktywnego programu musi
mieć zaznaczone **Sterowanie wprost**.

---

## 2. Wzorzec dodatku — cztery kroki

### Krok 1: wątek w tle z gniazdem

Nigdy w wątku UI — `recv()` blokuje, a zablokowany wątek UI to zamrożony CAD.

### Krok 2: bufor pod zamkiem

Sumuj przyrosty w słowniku chronionym `Lock`. Nie rysuj z tego wątku.

### Krok 3: przeskok na wątek główny

**To jest cała trudność.** Prawie żadne API CAD-a nie jest wielowątkowe;
wywołanie z wątku roboczego kończy się cichym brakiem efektu albo wywaleniem
programu. Każdy program ma na to własny mechanizm:

| Program | Sposób przejścia na wątek główny |
|---|---|
| Fusion 360 | `app.fireCustomEvent()` + `CustomEventHandler` |
| Blender | `bpy.app.timers.register()` (timer chodzi na wątku głównym) |
| Rhino / Grasshopper | `RhinoApp.InvokeOnUiThread()` |
| SolidWorks | `Control.BeginInvoke` na formie dodatku (WinForms) |
| Inventor | zdarzenie `OnIdle` albo timer WinForms |
| FreeCAD | `QTimer` w wątku GUI (Qt jak w MAKMOUSE) |
| Creo | pętla zdarzeń Toolkit / `ProAsync…` (patrz niżej) |

### Krok 4: ruszenie kamery

Wszędzie ten sam rachunek, tylko inne nazwy klas:

* **orbita** — obróć punkt `eye` wokół `target`: kąt odchylenia wokół pionu
  świata (żeby model się nie przechylał), kąt pochylenia wokół poziomej osi
  kamery (`forward × up`);
* **przesuwanie** — przesuń `eye` **i** `target` o ten sam wektor w płaszczyźnie
  ekranu, skalowany odległością kamery (inaczej przy zoomie ruch jest za szybki
  albo za wolny);
* **zoom** — skala **wykładnicza** (`exp(-d * k)`), nie odejmowanie odległości.
  Dzięki temu przybliżanie i oddalanie są symetryczne i nigdy nie przejdziesz
  przez cel. Uwaga na kamerę ortograficzną: tam przesunięcie oka nic nie zmienia,
  trzeba ruszyć „rozpiętość widoku" (`viewExtents` w Fusionie, analogicznie
  gdzie indziej).

Referencja: [fusion_addin/MAKMOUSE/MAKMOUSE.py](fusion_addin/MAKMOUSE/MAKMOUSE.py) —
funkcja `_apply()` to dokładnie ta matematyka, w 60 linijkach.

### Szkielet klienta (Python — Blender, Rhino, FreeCAD)

```python
import json, socket, threading

HOST, PORT = "127.0.0.1", 8765
_stop = threading.Event()
_lock = threading.Lock()
_pending = {"x": 0.0, "y": 0.0, "zoom": 0.0}
_mode = "orbit"

def _reader():
    while not _stop.is_set():
        try:
            sock = socket.create_connection((HOST, PORT), timeout=2.0)
            sock.settimeout(0.4)
            buf = b""
            while not _stop.is_set():
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    _consume(line)
        except OSError:
            pass                      # MAKMOUSE jeszcze nie wstał
        _stop.wait(1.0)               # i tak spróbujemy za sekundę

def _consume(line):
    global _mode
    try:
        msg = json.loads(line.decode("utf-8"))
    except ValueError:
        return
    with _lock:
        if msg.get("t") == "axis":
            _pending["x"] += float(msg.get("x", 0.0))
            _pending["y"] += float(msg.get("y", 0.0))
        elif msg.get("t") == "zoom":
            _pending["zoom"] += float(msg.get("d", 0.0))
        elif msg.get("t") == "mode":
            _mode = msg.get("mode", "orbit") if msg.get("on") else "orbit"

def take():
    """Wołane z wątku głównego: zabiera zebrane przyrosty i zeruje bufor."""
    with _lock:
        dx, dy, dz = _pending["x"], _pending["y"], _pending["zoom"]
        _pending["x"] = _pending["y"] = _pending["zoom"] = 0.0
        return dx, dy, dz, _mode
```

Zostaje podpiąć `take()` pod timer programu i zamienić wynik na kamerę.

---

## 3. Creo Parametric — konkretnie

Creo jest inne niż Fusion pod jednym istotnym względem: **nie ma wbudowanego
Pythona**. Automatyzację robi się przez jedno z API PTC:

| API | Język | Uwagi |
|---|---|---|
| **Creo Toolkit** | C | najpełniejsze, tryb synchroniczny (DLL) albo **asynchroniczny (osobny `.exe`)** |
| **J-Link** | Java | ten sam zestaw funkcji, bez kompilatora C — dobre na start |
| **VB API** | VB.NET / C# | wygodne, ale węższe |
| **Creo Object TOOLKIT C++/Java** | C++ / Java | obiektowa nakładka na Toolkit |

Wszystkie wymagają licencji deweloperskiej PTC (dostęp przez program partnerski
albo licencję edukacyjną).

### Droga najprostsza: aplikacja **asynchroniczna**

Tryb asynchroniczny to zwykły program, który **łączy się z działającą sesją
Creo** — nie trzeba budować DLL-a ani rejestrować dodatku, można go uruchamiać
i zatrzymywać niezależnie i debugować normalnym debuggerem. Do tego pasuje
idealnie, bo MAKMOUSE i tak stoi obok jako osobny proces.

Szkielet (J-Link/Java, bo bez kompilatora C):

```java
// 1. połącz się z działającą sesją Creo
Session session = pfcGlobal.GetProESession();      // async: GetProESession / ConnectToProE

// 2. wątek w tle czyta linie JSON z 127.0.0.1:8765 i sumuje przyrosty
//    (kod jak w szkielecie powyżej, tylko po javowemu)

// 3. na tiku (timer / pętla zdarzeń) zabierz przyrosty i rusz kamerę
Window window   = session.GetCurrentWindow();
View   view     = window.GetModel().RetrieveCurrentView();   // albo GetView(...)
Matrix3D m      = view.GetTransform();                       // macierz widoku
// zmodyfikuj m: obrót wokół pionu świata + osi poziomej kamery, skala dla zoomu
view.SetTransform(m);
window.Repaint();
```

W Toolkicie C te same kroki nazywają się mniej więcej tak (sprawdź dokładne
sygnatury w *Creo Toolkit Reference* dla swojej wersji — PTC zmieniało je
między wydaniami):

* `ProWindowCurrentGet()` — bieżące okno,
* `ProViewMatrixGet()` / `ProViewMatrixSet()` — **macierz widoku, czyli serce
  sprawy**: to nią kręcisz zamiast liczyć `eye`/`target`,
* `ProWindowRefresh()` — przerysowanie,
* `ProViewRetrieve()` — widoki nazwane (FRONT, TOP, RIGHT, DEFAULT), czyli
  gotowa obsługa komunikatu `{"t":"view"}`,
* `ProViewRefit()` / `ProWindowFit()` — dopasowanie do okna.

Uwaga na różnicę wobec Fusiona: Creo operuje **macierzą widoku**, a nie parą
`eye`/`target`. To upraszcza sprawę — orbita to wymnożenie macierzy przez obrót,
przesuwanie to dołożenie translacji, zoom to skala. Nie musisz odtwarzać
`crossProduct` i normalizacji z kodu Fusiona.

### Zanim to napiszesz: sprawdź trzy rzeczy

**1. Emulacja przeciągania może wystarczyć.** Creo świetnie obsługuje nawigację
myszą (ŚPM = obrót, `Shift`+ŚPM = przesuwanie, `Ctrl`+ŚPM = zoom). Wystarczy
dodać w MAKMOUSE profil bez *Sterowania wprost*:

| Pole | Wartość |
|---|---|
| Nazwa | `Creo` |
| Pliki .exe | `xtop.exe`, `parametric.exe` |
| Orbita | trzymaj: *(nic)*, przycisk: **SPM** |
| Przesuwanie | trzymaj: **Shift**, przycisk: **SPM** |
| Zoom | sposób: **Kółko myszy** |
| Gest *Ruch myszy* | trzymaj: *(nic)*, przycisk: **SPM** |

To działa **od razu, bez pisania linijki kodu**. Kosztem jest to, że w trakcie
gestu rusza się kursor — dokładnie ten problem, który dodatek eliminuje.

**2. Creo natywnie obsługuje komercyjne manipulatory 3D.** Jeżeli celem jest
sama funkcjonalność, a nie własny protokół, drugą drogą jest zgłaszanie się
firmware'u jako taki manipulator (cudze VID/PID + sterownik jego producenta).
Wtedy Creo, SolidWorks, Rhino i cała reszta obsługują urządzenie bez jednego
dodatku — ceną jest użycie cudzego identyfikatora producenta i uzależnienie od
jego sterownika.

**3. Licencja deweloperska.** Toolkit i J-Link nie działają bez niej. Zanim
zaplanujesz tydzień pracy, sprawdź, czy Twoja licencja Creo ją obejmuje.

### Jak zainstalować gotowy dodatek Creo

Dodatek asynchroniczny to zwykły `.exe`/`.jar` — uruchamiasz go po starcie Creo
(albo z autostartu). Dodatek synchroniczny rejestruje się plikiem
`protk.dat` w katalogu startowym Creo albo w `<creo>\text\`:

```
name            makmouse
STARTUP         dll
EXEC_FILE       C:\MAKMOUSE\creo\makmouse_creo.dll
TEXT_DIR        C:\MAKMOUSE\creo\text
END
```

---

## 4. Pozostałe programy — od czego zacząć

| Program | Typ dodatku | Punkt startu |
|---|---|---|
| **Blender** | skrypt Python | `bpy.app.timers.register()`, kamera przez `bpy.context.space_data.region_3d` (`view_rotation`, `view_location`, `view_distance`) |
| **Rhino** | wtyczka Python / RhinoCommon | `RhinoApp.InvokeOnUiThread`, kamera przez `RhinoView.ActiveViewport.SetCameraLocation/SetCameraTarget` |
| **FreeCAD** | skrypt Python | `QTimer`, kamera przez `Gui.ActiveDocument.ActiveView` (Coin3D) |
| **SolidWorks** | dodatek COM (C#/VB.NET) | `IModelDoc2.ActiveView`, `IModelView.RotateAboutAxis`, `Translate3`, `ZoomByFactor` |
| **Inventor** | dodatek .NET | `Camera` z `View.Camera`, `Camera.Apply()` |
| **SketchUp** | rozszerzenie Ruby | `Sketchup.active_model.active_view.camera` |

Blender, Rhino i FreeCAD mają Pythona w środku, więc szkielet klienta z punktu 2
wkleja się tam praktycznie bez zmian — to najlepsze miejsce na drugi dodatek po
Fusionie.

---
---

# Add-ins for other CAD applications (Creo, SolidWorks, Rhino, Blender…)

The Fusion add-in is nothing special — it is **60 lines of logic** wrapped in one
application's API. All the hard parts (reading HID, profiles, axis filtering) live
in MAKMOUSE and are shared. The add-in does three things:

1. connects to MAKMOUSE over a TCP socket,
2. reads JSON lines and accumulates the deltas,
3. translates them into camera moves **on the application's main thread**.

Below: the protocol, the pattern, and what specifically to do in Creo.

---

## 1. The bridge protocol

MAKMOUSE is the **server** and listens on `127.0.0.1:8765` (the port is
configurable through `"bridge_port"`). The add-in is the **client** and keeps
retrying, because nothing guarantees the order in which the programs start.

Format: **one JSON object per line, UTF-8, terminated with `\n`**. Nearly all
traffic goes from MAKMOUSE to the add-in; the add-in sends one greeting at most.

**Greetings (since 1.4.0).** Right after connecting MAKMOUSE sends
`{"t":"hello","server":"MAKMOUSE","device":"MAKMOUSE","version":"1.4.0"}`
(`device` is the string from the device's USB descriptor). The add-in may answer
`{"t":"hello","app":"<application>"}` — MAKMOUSE then sends the axes only to the
add-in whose application is chosen in the profile's **Add-in** list (`"addon"` in
the configuration). An add-in that doesn't introduce itself (the Fusion add-in)
counts as `fusion`. SolidCraft introduces itself as `solidcraft`. A new add-in for
another application needs a new entry in `ADDONS` in
[makmouse/profiles.py](makmouse/profiles.py) and a constant in
[makmouse/bridge.py](makmouse/bridge.py).

| Message | When | Meaning |
|---|---|---|
| `{"t":"axis","x":1.5,"y":-3.0}` | knob movement | axis delta in device units (±127 per report, sensitivity already applied) |
| `{"t":"zoom","d":1.0}` | ring rotation | signed encoder clicks |
| `{"t":"mode","mode":"pan","on":true}` | side button with the *3D navigation* action | the mode the axes should drive: `orbit` \| `pan` \| `zoom` |
| `{"t":"view","name":"iso"}` | side button with the *View* action | standard view: `front`, `back`, `left`, `right`, `top`, `bottom`, `iso`, `fit` |

Two properties worth remembering:

* **axes are relative** — there is no absolute position, every packet says "move
  by this much";
* **packets may be dropped** under congestion (MAKMOUSE discards the oldest in the
  queue). In a stream of deltas that does no harm — fresher data matters more than
  completeness.

You can watch the stream without any CAD at all:

```powershell
python -c "import socket;s=socket.create_connection(('127.0.0.1',8765));[print(l) for l in s.makefile()]"
```

Move the knob — if JSON lines scroll by, the bridge works and any problem is on the
add-in side, not MAKMOUSE. Condition: the profile of the active application must
have **Direct control** ticked.

---

## 2. The add-in pattern — four steps

### Step 1: a background thread with the socket

Never on the UI thread — `recv()` blocks, and a blocked UI thread is a frozen CAD.

### Step 2: a buffer behind a lock

Accumulate deltas in a dictionary guarded by a `Lock`. Do not draw from that
thread.

### Step 3: the hop to the main thread

**This is the whole difficulty.** Almost no CAD API is thread-safe; a call from a
worker thread ends in a silent no-op or a crash. Every application has its own
mechanism:

| Application | How to get onto the main thread |
|---|---|
| Fusion 360 | `app.fireCustomEvent()` + `CustomEventHandler` |
| Blender | `bpy.app.timers.register()` (the timer runs on the main thread) |
| Rhino / Grasshopper | `RhinoApp.InvokeOnUiThread()` |
| SolidWorks | `Control.BeginInvoke` on the add-in's form (WinForms) |
| Inventor | the `OnIdle` event or a WinForms timer |
| FreeCAD | a `QTimer` on the GUI thread (Qt, as in MAKMOUSE) |
| Creo | the Toolkit event loop / `ProAsync…` (see below) |

### Step 4: moving the camera

The same arithmetic everywhere, only the class names differ:

* **orbit** — rotate `eye` around `target`: yaw around the world up axis (so the
  model does not tilt), pitch around the camera's horizontal axis
  (`forward × up`);
* **pan** — move `eye` **and** `target` by the same vector in the screen plane,
  scaled by the camera distance (otherwise the motion is too fast or too slow as
  you zoom);
* **zoom** — an **exponential** scale (`exp(-d * k)`), not a subtraction of the
  distance. That makes zooming in and out symmetric and you never pass through the
  target. Watch out for orthographic cameras: there, moving the eye changes
  nothing — you have to move the "view extent" (`viewExtents` in Fusion, the
  equivalent elsewhere).

Reference: [fusion_addin/MAKMOUSE/MAKMOUSE.py](fusion_addin/MAKMOUSE/MAKMOUSE.py) —
the `_apply()` function is exactly that maths, in 60 lines. The Python client
skeleton is in the Polish section above and pastes into Blender, Rhino or FreeCAD
essentially unchanged.

---

## 3. Creo Parametric — specifics

Creo differs from Fusion in one important way: **there is no built-in Python**.
Automation goes through one of PTC's APIs:

| API | Language | Notes |
|---|---|---|
| **Creo Toolkit** | C | the most complete; synchronous (DLL) or **asynchronous (a separate `.exe`)** mode |
| **J-Link** | Java | the same function set, no C compiler needed — a good start |
| **VB API** | VB.NET / C# | convenient, but narrower |
| **Creo Object TOOLKIT C++/Java** | C++ / Java | an object-oriented layer over Toolkit |

All of them require a PTC developer licence (through the partner programme or an
educational licence).

### The easiest route: an **asynchronous** application

Asynchronous mode is an ordinary program that **connects to a running Creo
session** — no DLL to build, no add-in to register, you can start and stop it
independently and debug it with a normal debugger. It fits perfectly here,
because MAKMOUSE already sits next to it as a separate process.

In Toolkit C the steps are named roughly as follows (check the exact signatures in
the *Creo Toolkit Reference* for your version — PTC has changed them between
releases):

* `ProWindowCurrentGet()` — the current window,
* `ProViewMatrixGet()` / `ProViewMatrixSet()` — **the view matrix, which is the
  heart of the matter**: you rotate that instead of computing `eye`/`target`,
* `ProWindowRefresh()` — redraw,
* `ProViewRetrieve()` — named views (FRONT, TOP, RIGHT, DEFAULT), i.e. a
  ready-made handler for the `{"t":"view"}` message,
* `ProViewRefit()` / `ProWindowFit()` — fit to window.

Note the difference from Fusion: Creo works with a **view matrix**, not an
`eye`/`target` pair. That simplifies things — orbit is a matrix multiplication by
a rotation, pan is an added translation, zoom is a scale. You do not need to
reproduce the `crossProduct` and normalisation from the Fusion code.

### Before you write it: check three things

**1. Drag emulation may be enough.** Creo handles mouse navigation well
(MMB = rotate, `Shift`+MMB = pan, `Ctrl`+MMB = zoom). It is enough to add a
MAKMOUSE profile *without* Direct control:

| Field | Value |
|---|---|
| Name | `Creo` |
| .exe files | `xtop.exe`, `parametric.exe` |
| Orbit | hold: *(nothing)*, button: **MMB** |
| Pan | hold: **Shift**, button: **MMB** |
| Zoom | style: **Mouse wheel** |
| *Mouse move* gesture | hold: *(nothing)*, button: **MMB** |

This works **immediately, without writing a line of code**. The cost is that the
cursor moves during the gesture — exactly the problem the add-in removes.

**2. Creo supports commercial 3D mice natively.** If the goal is the functionality
rather than your own protocol, the second route is to have the firmware present
itself as such a device (someone else's VID/PID + its maker's driver). Then Creo,
SolidWorks, Rhino and everything else support the device without a single add-in —
the cost is using somebody else's vendor identifier and depending on that driver.

**3. The developer licence.** Toolkit and J-Link do not work without one. Before
planning a week of work, check whether your Creo licence covers it.

### Installing a finished Creo add-in

An asynchronous add-in is an ordinary `.exe`/`.jar` — you start it after Creo
comes up (or from autostart). A synchronous add-in registers itself with a
`protk.dat` file in Creo's startup directory or in `<creo>\text\`; see the Polish
section above for the file contents.

---

## 4. Other applications — where to start

| Application | Add-in type | Starting point |
|---|---|---|
| **Blender** | Python script | `bpy.app.timers.register()`, camera via `bpy.context.space_data.region_3d` (`view_rotation`, `view_location`, `view_distance`) |
| **Rhino** | Python / RhinoCommon plug-in | `RhinoApp.InvokeOnUiThread`, camera via `RhinoView.ActiveViewport.SetCameraLocation/SetCameraTarget` |
| **FreeCAD** | Python script | `QTimer`, camera via `Gui.ActiveDocument.ActiveView` (Coin3D) |
| **SolidWorks** | COM add-in (C#/VB.NET) | `IModelDoc2.ActiveView`, `IModelView.RotateAboutAxis`, `Translate3`, `ZoomByFactor` |
| **Inventor** | .NET add-in | `Camera` from `View.Camera`, `Camera.Apply()` |
| **SketchUp** | Ruby extension | `Sketchup.active_model.active_view.camera` |

Blender, Rhino and FreeCAD have Python inside, so the client skeleton from section
2 pastes in practically unchanged — that is the best place for a second add-in
after Fusion.
