"""Instrukcja obsługi w programie - okno otwierane przyciskiem "i" w pasku górnym.

ZA CO ODPOWIADA
    * treść instrukcji po polsku i po angielsku (HTML wpisany w kod),
    * wybór wersji językowej według bieżącego języka interfejsu,
    * kolory instrukcji zgodne z motywem i kolorem wiodącym.
    Zmieniając działanie programu, warto dopisać zmianę tutaj (obie wersje).

NAJWAŻNIEJSZE ELEMENTY
    HelpDialog ........... okno z instrukcją
    _html_pl(), _html_en()  treść instrukcji
    _style() ............. style CSS instrukcji (kolory z theme.py)

POWIĄZANIA
    używa: theme.py, i18n.py, devices.py (nazwa urządzenia)
    używany przez: main_window.py (_show_help)
"""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from .. import APP_NAME, __version__
from .. import devices as dv
from ..i18n import language, tr
from . import theme as T


def _style() -> str:
    return f"""
<style>
  body {{ color: {T.TEXT}; }}
  h2 {{ color: {T.ACCENT}; font-size: 15px; margin-top: 18px; margin-bottom: 4px; }}
  h3 {{ font-size: 13px; margin-top: 12px; margin-bottom: 2px; }}
  p, li {{ font-size: 13px; line-height: 150%; }}
  code {{ color: {T.ACCENT_SOFT}; font-family: Consolas, monospace; }}
  .lead {{ color: {T.TEXT_DIM}; font-size: 13px; }}
  td {{ padding: 3px 12px 3px 0; font-size: 13px; }}
  th {{ padding: 3px 12px 3px 0; font-size: 12px; color: {T.TEXT_DIM}; text-align: left; }}
</style>
"""


def _html_pl() -> str:
    return _style() + f"""
<h1 style="font-size:18px; margin-bottom:2px;">{APP_NAME} {__version__}</h1>
<p class="lead">Sterownik własnej myszy 3D dla programów CAD.</p>

<h2>1. Podłączenie urządzenia</h2>
<p>Kropka w lewym górnym rogu obok napisu <b>{dv.TARGET_NAME}</b>:
<span style="color:{T.OK}">zielona</span> = urządzenie podłączone i aktywne,
<span style="color:{T.BAD}">czerwona</span> = brak urządzenia albo przełącznik
<i>Aktywny</i> jest wyłączony.</p>

<h2>2. Przyciski boczne</h2>
<p>Akcje ustawiasz w zakładce <b>Przyciski i gesty</b>:</p>
<table>
  <tr><th>Typ akcji</th><th>Co robi</th></tr>
  <tr><td>Nic</td><td>przycisk przechodzi dalej bez zmian</td></tr>
  <tr><td>Nawigacja 3D</td><td>orbita / przesuwanie / zoom, dopóki trzymasz</td></tr>
  <tr><td>Skrót klawiszowy</td><td>impuls przy naciśnięciu, np. <code>Ctrl+Z</code></td></tr>
  <tr><td>Przytrzymaj klawisze</td><td>trzyma kombinację do zwolnienia przycisku</td></tr>
  <tr><td>Widok (dodatek 3D)</td><td>ustawia widok standardowy przez dodatek 3D
      (Fusion 360 albo SolidCraft)</td></tr>
</table>
<p><b>Kwadracik w prawym górnym rogu kafla</b> wyłącza funkcję tego jednego
przycisku - ustawienia zostają zapisane, a przycisk przechodzi do systemu bez
zmian. W legendzie pod podglądem na żywo jego kropka robi się wtedy czerwona
(zielona = funkcja działa), tak jak kropka stanu urządzenia w pasku górnym.</p>
<p>Liczbę przycisków (3 albo 6) wybierasz w zakładce <b>Ustawienia</b>. Podgląd
na żywo i kafle zmieniają się razem z nią.</p>

<h2>3. Gesty ciągłe - ruch myszy i scroll</h2>
<p>Gałka wysyła zwykły ruch myszy, pierścień - scroll. W sekcji <b>Gesty ciągłe</b>
możesz dołożyć do nich modyfikator trzymany na czas gestu:</p>
<ul>
  <li><b>Ruch myszy bez modyfikatora</b> - zwykły ruch kursora,</li>
  <li><b>Ruch myszy + Shift i SPM</b> - orbita w Fusion 360 i Inventorze
      (ustawienie fabryczne),</li>
  <li><b>Scroll + Ctrl</b> - zoom krokowy; może być też dowolna litera,
      np. <i>scroll + H</i>.</li>
</ul>
<p>W polach "co trzymać" wystarczy nacisnąć <b>sam modyfikator</b> - Shift, Ctrl,
Alt albo ich kombinacje. Klawisz główny nie jest wymagany.</p>
<p>Gest kończy się sam: gałka i pierścień nie mają "puszczenia", więc modyfikator
jest zwalniany po 250 ms ciszy.</p>
<p>Przy włączonym <i>Sterowaniu wprost</i> ta sekcja znika - osie idą wtedy do
dodatku 3D i modyfikatory nie mają żadnego wpływu.</p>

<h2>4. Nawigacja 3D</h2>
<p>Przycisk z akcją <i>Nawigacja 3D</i> syntezuje pełny gest programu CAD:
wciska modyfikatory i przycisk myszy, zamienia osie X/Y na ruch kursora pozycją
bezwzględną (bez wpływu przyspieszenia wskaźnika), a przy krawędzi ekranu
przepina gest, żeby dało się obracać bez końca.</p>
<p>Fabrycznie: orbita = <code>Shift</code> + środkowy, przesuwanie = środkowy,
zoom = kółko. Dla innego programu wpisz własną kombinację w zakładce
<b>Nawigacja 3D</b>.</p>
<p><b>Cała ta zakładka należy do wybranego profilu</b> - każdy program ma własne
akordy, własne czułości i własne zachowanie kursora.</p>
<p>Cztery rzeczy warto znać:</p>
<ul>
  <li><b>Czułość - zoom (pierścień)</b> to skok jednego kliknięcia, a nie liczba
      impulsów na kliknięcie. Pierścień dalej daje 20 kliknięć na obrót; przy
      0.30 każde z nich przewija mniej wierszy i podchodzi do bryły bliżej, przy
      2.50 skacze dalej. Ta sama wartość działa na scroll i na kamerę w dodatku.</li>
  <li><b>Czułość - orbita</b> i <b>Czułość - przesuwanie</b> obowiązują wtedy, gdy
      przycisk boczny trzyma akcję <i>Nawigacja 3D</i> - także jako przełącznik.
      Gałka dostaje wtedy tempo tego trybu zamiast <i>Czułości - ruch gałki</i>.</li>
  <li><b>Zostaw kursor w nowym miejscu</b> decyduje, czy po geście wskaźnik
      zostaje tam, dokąd dojechał (fabrycznie), czy wraca na poprzednią pozycję.</li>
  <li><b>Odwróć zoom</b> odwraca kierunek obrotu pierścienia - przybliżanie
      zamienia się z oddalaniem, w scrollu i w zoomie przez dodatek 3D.</li>
</ul>

<h2>5. Profile</h2>
<p>Profil przełącza się sam według aktywnego programu - decyduje lista plików
<code>.exe</code> w profilu. Profil oznaczony <i>(domyślny)</i> obowiązuje
wszędzie tam, gdzie nie pasuje żaden inny.</p>
<p><b>Kwadracik przy nazwie na liście</b> włącza i wyłącza cały profil.</p>
<p><b>Sterowanie wprost (dodatek 3D)</b> w zakładce <b>Nawigacja 3D</b> wysyła osie
prosto do programu, który sam przestawia kamerę - kursor się nie rusza i zwykła
mysz pracuje niezależnie. Lista <b>Dodatek</b> obok wybiera program:
<i>Fusion 360</i> (dodatek MAKMOUSE uruchomiony w Fusionie) albo <i>SolidCraft</i>
(w SolidCrafcie: Preferencje &rarr; Nawigacja &rarr; Mysz 3D &rarr; <i>Nawiguj
programem urządzenia na tym komputerze</i>). Osie trafiają tylko do wybranego
programu; bez połączenia profil wraca do emulacji przeciągania.</p>

<h2>6. Monitor - gdy coś nie działa</h2>
<p>Zakładka <b>Monitor</b> pokazuje na żywo wciśnięte przyciski, stan osi
i surowe bajty raportu. Jeśli po naciśnięciu przycisku nie widać linii
"przycisk boczny N DÓŁ", porównaj bajty raportu z ustawieniami w zakładce
<b>Urządzenie</b>.</p>

<h2>7. Konfiguracja, język i skrót awaryjny</h2>
<p>Ustawienia zapisują się same. Domyślnie w <code>%APPDATA%\\MAKMOUSE</code>,
ale w zakładce <b>Ustawienia</b> możesz wskazać dowolną inną ścieżkę - pendrive,
folder projektu, chmurę.</p>
<p>W tej samej zakładce jest lista <b>Język</b>: polski i angielski. Po wyborze
okno wstaje od nowa w nowym języku, a wybór zostaje zapamiętany. Obok są też
<b>Liczba przycisków bocznych</b> (3 albo 6) i <b>Kolor wiodący</b> - dziesięć
barw do wyboru, zmieniane w locie.</p>
<p>Skrót awaryjny (fabrycznie <code>Ctrl+Alt+F12</code>) zwalnia wszystkie
trzymane klawisze i przełącza MAKMOUSE w stan wyłączony. Użyj go, gdyby coś
się zacięło.</p>
"""


def _html_en() -> str:
    return _style() + f"""
<h1 style="font-size:18px; margin-bottom:2px;">{APP_NAME} {__version__}</h1>
<p class="lead">Driver for your own 3D mouse, made for CAD applications.</p>

<h2>1. Connecting the device</h2>
<p>The dot in the top-left corner next to <b>{dv.TARGET_NAME}</b>:
<span style="color:{T.OK}">green</span> = device connected and active,
<span style="color:{T.BAD}">red</span> = no device, or the <i>Active</i> switch
is off.</p>

<h2>2. Side buttons</h2>
<p>Actions are configured on the <b>Buttons and gestures</b> tab:</p>
<table>
  <tr><th>Action type</th><th>What it does</th></tr>
  <tr><td>Nothing</td><td>the button passes through unchanged</td></tr>
  <tr><td>3D navigation</td><td>orbit / pan / zoom for as long as you hold it</td></tr>
  <tr><td>Keyboard shortcut</td><td>one pulse on press, e.g. <code>Ctrl+Z</code></td></tr>
  <tr><td>Hold keys</td><td>holds the combination until the button is released</td></tr>
  <tr><td>View (3D add-in)</td><td>sets a standard view through the 3D add-in
      (Fusion 360 or SolidCraft)</td></tr>
</table>
<p>The <b>box in the top-right corner of a tile</b> switches off the function of
that one button - its settings are kept and the button goes to the system
unchanged. Its dot in the legend under the live preview then turns red (green =
the function is on), just like the device state dot in the top bar.</p>
<p>The number of buttons (3 or 6) is chosen on the <b>Settings</b> tab. The live
preview and the tiles follow it.</p>

<h2>3. Continuous gestures - mouse move and scroll</h2>
<p>The knob sends ordinary mouse movement, the ring sends scroll. In the
<b>Continuous gestures</b> section you can attach a modifier that is held for the
duration of the gesture:</p>
<ul>
  <li><b>Mouse move with no modifier</b> - plain cursor movement,</li>
  <li><b>Mouse move + Shift and MMB</b> - orbit in Fusion 360 and Inventor
      (factory setting),</li>
  <li><b>Scroll + Ctrl</b> - stepped zoom; it can also be any letter,
      e.g. <i>scroll + H</i>.</li>
</ul>
<p>In the "what to hold" fields it is enough to press <b>the modifier alone</b> -
Shift, Ctrl, Alt or their combinations. A main key is not required.</p>
<p>The gesture ends by itself: the knob and the ring have no "release", so the
modifier is let go after 250 ms of silence.</p>
<p>With <i>Direct control</i> on, this section disappears - the axes go to the 3D
add-in then and modifiers have no effect at all.</p>

<h2>4. 3D navigation</h2>
<p>A button bound to <i>3D navigation</i> synthesises the full CAD gesture: it
presses the modifiers and the mouse button, turns the X/Y axes into absolute
cursor movement (immune to pointer acceleration), and re-anchors the gesture at
the screen edge so you can keep rotating forever.</p>
<p>Factory setting: orbit = <code>Shift</code> + middle, pan = middle,
zoom = wheel. For a different application enter your own combination on the
<b>3D navigation</b> tab.</p>
<p><b>The whole tab belongs to the selected profile</b> - every application gets
its own chords, sensitivities and cursor behaviour.</p>
<p>Four things worth knowing:</p>
<ul>
  <li><b>Sensitivity - zoom (ring)</b> is the step of one click, not the number of
      impulses per click. The ring still gives 20 clicks per turn; at 0.30 each of
      them scrolls fewer lines and approaches the model closer, at 2.50 it jumps
      further. The same value drives the scroll and the camera in the add-in.</li>
  <li><b>Sensitivity - orbit</b> and <b>Sensitivity - pan</b> apply while a side
      button holds the <i>3D navigation</i> action - also as a toggle. The knob
      then takes the pace of that mode instead of <i>Sensitivity - knob</i>.</li>
  <li><b>Leave the cursor where the gesture ended</b> decides whether the pointer
      stays where it arrived (the default) or returns to its previous position.</li>
  <li><b>Invert zoom</b> reverses the ring's direction - zooming in becomes
      zooming out, in scrolling and in zoom through the 3D add-in.</li>
</ul>

<h2>5. Profiles</h2>
<p>The profile switches by itself according to the active application - the list
of <code>.exe</code> files in the profile decides. The profile marked
<i>(default)</i> applies everywhere no other profile matches.</p>
<p><b>The box next to the name in the list</b> switches a whole profile on and
off.</p>
<p><b>Direct control (3D add-in)</b> on the <b>3D navigation</b> tab sends the axes
straight to the application, which moves the camera itself - the cursor stays
put and your ordinary mouse works independently. The <b>Add-in</b> list next to it
picks the application: <i>Fusion 360</i> (the MAKMOUSE add-in running in Fusion) or
<i>SolidCraft</i> (in SolidCraft: Preferences &rarr; Navigation &rarr; 3D mouse &rarr;
<i>Navigate with a device app on this computer</i>). The axes reach the chosen
application only; without a connection the profile falls back to drag emulation.</p>

<h2>6. Monitor - when something does not work</h2>
<p>The <b>Monitor</b> tab shows pressed buttons, axis state and the raw report
bytes live. If pressing a button produces no "side button N DOWN" line, compare
the report bytes with the settings on the <b>Device</b> tab.</p>

<h2>7. Configuration, language and the panic hotkey</h2>
<p>Settings save themselves. By default into <code>%APPDATA%\\MAKMOUSE</code>,
but on the <b>Settings</b> tab you can point to any other path - a USB stick, a
project folder, a cloud-synced directory.</p>
<p>The same tab holds the <b>Language</b> list: Polish and English. After you
choose, the window is rebuilt in the new language and the choice is remembered.
Next to it are <b>Number of side buttons</b> (3 or 6) and <b>Accent colour</b> -
ten colours to choose from, applied on the fly.</p>
<p>The panic hotkey (<code>Ctrl+Alt+F12</code> by default) releases every held
key and switches MAKMOUSE off. Use it if anything ever gets stuck.</p>
"""


def _html() -> str:
    return _html_en() if language() == "en" else _html_pl()


class HelpDialog(QDialog):
    """Instrukcja obsługi - otwierana ikoną 'i' w pasku górnym."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("{app} - instrukcja obsługi").format(app=APP_NAME))
        self.setMinimumSize(660, 520)
        self.resize(820, 680)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(10)

        view = QTextBrowser()
        view.setOpenExternalLinks(False)
        view.setHtml(_html())
        lay.addWidget(view, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close = QPushButton(tr("Zamknij"))
        close.setObjectName("Primary")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        lay.addLayout(buttons)
