# MAKMOUSE CAD Software 1.4.1

*English version: [README.en.md](README.en.md)*

Sterownik własnej myszy 3D dla programów CAD (Fusion 360, SolidCraft, Inventor). Zamienia
gałkę, pierścień i przyciski boczne (trzy albo sześć — do wyboru w *Ustawieniach*)
w pełną nawigację 3D — jak w profesjonalnych manipulatorach 3D, ale na Twoim
sprzęcie.

Python + PySide6, wszystko poniżej GUI na czystym `ctypes` — bez pywin32,
bez sterowników, bez zewnętrznych bibliotek HID.

---

## W planach

* **Trzy osie gałki naraz.** Dziś gałka daje dwie osie (X/Y), a pierścień —
  zoom. W kolejnych wersjach planowana jest obsługa trzech osi jednocześnie, tak
  jak w profesjonalnych manipulatorach 3D: nowy układ raportu w firmware,
  osobne czułości i odwrócenia dla każdej osi oraz przekazywanie trzeciej osi
  mostem do dodatków (Fusion 360, SolidCraft).

---

## Co nowego w 1.4.1

* **Odwróć zoom** — nowe pole w *Nawigacja 3D → Osie X/Y*, obok *Zamień X/Y*.
  Odwraca kierunek obrotu pierścienia: przybliżanie zamienia się z oddalaniem,
  w zwykłym scrollu i w zoomie przez dodatek 3D (Fusion, SolidCraft). Jak reszta
  tej sekcji należy do profilu.

---

## Co nowego w 1.4.0

* **Sterowanie wprost także w SolidCrafcie.** Obok *Sterowanie wprost (dodatek
  3D)* jest lista **Dodatek**: *Fusion 360* albo *SolidCraft*. SolidCraft nie
  potrzebuje osobnej wtyczki — sam łączy się z mostem MAKMOUSE, gdy w nim
  włączysz *Preferencje → Nawigacja → Mysz 3D → Nawiguj programem urządzenia na
  tym komputerze*. Kamera rusza się bez udziału kursora, a zwykła mysz pracuje
  niezależnie.
* **Osie trafiają tylko do wybranego programu.** Dodatki przedstawiają się mostowi,
  więc przy uruchomionym Fusionie i SolidCrafcie naraz gałka rusza kamerą tylko
  w programie z aktywnego profilu.
* **Nowy profil fabryczny SolidCraft** (`solidcraft.exe`): sterowanie wprost,
  przycisk 1 = przesuwanie, 2 = `Ctrl+Z`, 3 = dopasuj widok. Starsza konfiguracja
  dostaje go automatycznie przy pierwszym uruchomieniu.
* *Widok Fusion* nazywa się teraz **Widok (dodatek 3D)** — działa w Fusionie
  i w SolidCrafcie.
* Most zauważa zamknięcie programu od razu, a nie dopiero przy kolejnej wysyłce —
  profil szybciej wraca do emulacji przeciągania.

---

## Co nowego w 1.3.3

* **Czułość zoomu to teraz skok przybliżenia, nie liczba impulsów.** Jedno
  kliknięcie na impuls pierścienia jak dotąd, ale o zmienionej wadze: strona
  przewija się o mniej wierszy, a kamera podchodzi do bryły o mniejszy kawałek —
  zamiast zmuszać do kręcenia pierścieniem więcej razy.
* **Czułość orbity i przesuwania działa też przy sterowaniu wprost.** Przycisk
  z akcją *Nawigacja 3D* (także jako przełącznik) nadaje osiom czułość swojego
  trybu, niezależnie od suwaka *Czułość — ruch gałki*.
* Jeden suwak zoomu zamiast dwóch — ten sam skok obowiązuje pierścień i akcję
  *Nawigacja 3D → Zoom*.
* Podgląd na żywo wrócił do **legendy pod grafiką**; stan funkcji przycisku
  pokazuje przy niej **zielona albo czerwona kropka**, tak jak stan urządzenia
  w pasku górnym.
* *Sterowanie wprost (dodatek 3D)* przeniesione na dół sekcji *Osie X/Y*, do
  reszty pól wyboru.

---

## Co nowego w 1.3.2

* **Czułość zoomu (pierścień) wreszcie działa** — wcześniej suwak nie wpływał na
  zwykły scroll (sposób działania zmieniony w 1.3.3, patrz wyżej).
* **Gałka rusza kursorem bez modyfikatora.** Pusty gest ruchu nie blokuje już
  osi — poza Fusionem nie trzeba wpisywać `Shift`, żeby cokolwiek się działo.
* **Zakładka *Nawigacja 3D* jest teraz osobna dla każdego profilu** (czułości,
  odwrócenia, zachowanie kursora). Stara konfiguracja przenosi się sama.
* **Nowe pole *Zostaw kursor w nowym miejscu*** — decyduje, czy po geście
  wskaźnik zostaje tam, dokąd dojechał, czy wraca na poprzednią pozycję.
* **Sterowanie wprost (dodatek 3D)** przeniesione do *Nawigacja 3D → Osie X/Y*,
  razem ze stanem dodatku. Przy włączonym sterowaniu wprost sekcja *Gesty ciągłe*
  znika zamiast się wyszarzać.
* **Włącznik profilu przy jego nazwie** na liście; **włącznik funkcji w rogu
  każdego kafla przycisku**.
* **Wybór 3 albo 6 przycisków bocznych** w *Ustawieniach* — razem z podglądem
  i zakładką przycisków.
* **Kolor wiodący aplikacji** do wyboru z dziesięciu barw.
* **Cały interfejs zwarty** — zakładki mieszczą się bez przewijania na mniejszym
  ekranie.
* **[build_exe.bat](build_exe.bat)** — generowanie gotowego `.exe` jednym
  kliknięciem.

---

## Instalacja i uruchomienie

```powershell
python -m pip install PySide6-Essentials
python d:\MAKKEY\run.py
```

Bez okna konsoli: [MAKMOUSE.bat](MAKMOUSE.bat) albo `pythonw run.py`.

Gotowy `.exe` (bez instalowania Pythona) i przenoszenie projektu na inny
komputer: **[INSTALL.md](INSTALL.md)**.

---

## Język interfejsu

Zakładka *Ustawienia* → **Język**: `Polski` i `English`. Wybór jest zapisywany
w konfiguracji (`"language": "pl" | "en"`), więc po ponownym uruchomieniu okno
wstaje w tym samym języku.

Tłumaczenia trafiają do kontrolek w chwili ich tworzenia, więc po zmianie języka
okno jest **budowane od nowa**. Silnik, kontroler i most żyją przez cały ten czas,
więc urządzenie nie przestaje działać nawet na moment — znika tylko okno i wraca
przetłumaczone.

Nowe teksty dodaje się w [makmouse/i18n.py](makmouse/i18n.py): kluczem jest polski
tekst źródłowy, wartością tłumaczenie. Brak wpisu nie wywraca interfejsu — pokazuje
się wtedy polski oryginał.

---

## Instrukcja w aplikacji

Okrągły przycisk **i** w prawym górnym rogu otwiera pełną instrukcję obsługi —
to samo, co poniżej, ale bez wychodzenia z programu.

## Motyw jasny i ciemny

Dwupozycyjny przełącznik obok przycisku **i**: **słońce** = motyw jasny,
**księżyc** = ciemny. Przełącza całą paletę w locie, bez restartu, a wybór jest
zapisywany w konfiguracji — po ponownym uruchomieniu okno wstaje w wybranym
motywie.

## Kolor wiodący

*Ustawienia* → **Kolor wiodący**: dziesięć podstawowych barw (niebieski —
fabryczny, granatowy, fioletowy, różowy, czerwony, pomarańczowy, żółty, zielony,
turkusowy, grafitowy). Nie ma pełnej palety RGB celowo — krótka lista trzyma
interfejs spójnym.

Wybrany kolor przechodzi przez całą aplikację od razu, bez restartu: przełączniki,
zaznaczenia, suwaki, podkreślenie zakładki, świecący pierścień na grafice, ikona
w zasobniku i podświetlenia w podglądzie na żywo. Odcienie *hover* i *pressed*
wyliczane są z niego automatycznie.

## Liczba przycisków bocznych

*Ustawienia* → **Liczba przycisków bocznych**: `3 przyciski` albo `6 przycisków`.
Wybór przestawia od razu zakładkę *Przyciski i gesty* (kafle), podgląd na żywo
(rysunek opaski) i lampki w *Monitorze*.

Ustawienia przycisków spoza wybranej liczby **nie giną** — zostają zapisane
w profilu i wracają po ponownym wybraniu wersji sześcioprzyciskowej.

---

## Gdzie leży konfiguracja

Domyślnie `%APPDATA%\MAKMOUSE\config.json`, ale w zakładce *Ustawienia* →
**Plik konfiguracji** można wskazać dowolną inną ścieżkę — pendrive, folder
projektu, katalog synchronizowany z chmurą.

* *Zmień lokalizację…* zapisuje bieżące ustawienia w nowym miejscu i od tej
  chwili wszystko idzie tam. Stary plik zostaje nietknięty — nic nie jest
  kasowane, decyzja o sprzątaniu należy do Ciebie.
* *Wróć do domyślnej* przywraca `%APPDATA%`.

Sama lokalizacja jest zapamiętywana w `%APPDATA%\MAKMOUSE\location.json` —
to jedyny plik, który zawsze zostaje w APPDATA, bo od czegoś trzeba zacząć.
Jeśli wskazany plik zniknie (np. odłączony pendrive), MAKMOUSE startuje
z ustawieniami domyślnymi i wypisuje o tym komunikat, zamiast po cichu
nadpisywać cokolwiek.

*Eksportuj / Importuj* to co innego: jednorazowa kopia do pliku i z pliku,
bez zmiany miejsca zapisu.

---

## Rozpoznawanie urządzenia

**MAKMOUSE nie ma wyboru urządzenia.** Aplikacja przegląda wszystkie kolekcje
HID widoczne dla Raw Input, czyta z każdej łańcuch producenta i produktu
(`HidD_GetManufacturerString` / `HidD_GetProductString`) i reaguje **wyłącznie**
na te, w których występuje napis `MAKMOUSE`. Każda inna mysz, klawiatura czy
tablet są ignorowane — nie da się przypadkiem przechwycić cudzego sprzętu.

W firmware wystarczy więc ustawić deskryptor USB tak, żeby `iProduct` lub
`iManufacturer` zawierał `MAKMOUSE`. Nazwa jest wykrywana niezależnie od
VID/PID, więc możesz je zmieniać bez ruszania aplikacji.

Urządzenie zgłasza się jako **jedna kolekcja: Multi-axis Controller**
(`Usage Page 0x01` / `Usage 0x08`) — ta sama klasa, w której pracują
profesjonalne manipulatory 3D. Osie, scroll i przyciski przychodzą jednym
raportem HID.

Stan pokazuje **kolorowa kropka obok napisu MAKMOUSE** w pasku górnym: zielona
= urządzenie podłączone i aktywne, czerwona = brak urządzenia albo przełącznik
*Aktywny* jest wyłączony. Pełny opis stanu jest w zakładce *Urządzenie*.
Hot-plug jest obsługiwany — po podpięciu urządzenia lista odświeża się sama.

---

## Grafika = podgląd na żywo

Rysunek urządzenia w środku okna jest wskaźnikiem stanu:

* **przycisk boczny** — zapala się kolorem wiodącym po naciśnięciu,
* **gałka** — odchyla się w stronę ruchu i pokazuje strzałkę kierunku,
* **pierścień** — rozjaśnia się i pokazuje grot w stronę obrotu.

Pod rysunkiem jest **legenda** z aktualnym przypisaniem każdego elementu:
przycisków bocznych, gałki (*Ruch myszy*) i pierścienia (*Scroll*). Przy każdym
przycisku stoi **zielona albo czerwona kropka** — dokładnie taka, jaka w pasku
górnym pokazuje stan całego urządzenia. Czerwona znaczy, że funkcja tego przycisku
jest wyłączona kwadracikiem w rogu jego kafla; przypisana akcja jest nadal
wypisana, żeby było wiadomo, co wróci po włączeniu.

Rysunek i legenda zmieniają się razem z wyborem **3 albo 6 przycisków**
w *Ustawieniach*.

Zakładka *Monitor* pokazuje dodatkowo pole **Wciśnięte przyciski**: nazwę
aktualnie trzymanego przycisku i podświetlone kafelki wszystkich.

---

## Co robi urządzenie i co MAKMOUSE do tego dokłada

Cały sprzęt mieści się w jednym raporcie HID (5 bajtów, Report ID 1):

| offset | pole | co to jest | nazwa w aplikacji |
|---|---|---|---|
| 0 | Report ID = 1 | — | — |
| 1 | X (`0x30`) | gałka, oś pozioma | *Ruch myszy* |
| 2 | Y (`0x31`) | gałka, oś pionowa | *Ruch myszy* |
| 3 | Rz (`0x35`) | enkoder pierścienia (20 impulsów na obrót) | *Scroll* |
| 4 | bity 0–5 | przyciski boczne | *Przycisk boczny 1–6* |

Bity przycisków czytane są wszystkie, ale do akcji trafia tylko tyle, ile ma
urządzenie według *Ustawienia → Liczba przycisków bocznych* (3 albo 6). Wersja
trzyprzyciskowa używa bitów 0–2, sześcioprzyciskowa dokłada bity 3–5 tego samego
bajtu.

Osie i enkoder są 8-bitowe ze znakiem i **przyrostowe** (`Relative`) — każdy
raport niesie zmianę, nie pozycję. Fabryczne ustawienia aplikacji dokładnie temu
odpowiadają, więc po podłączeniu nie trzeba niczego konfigurować.

MAKMOUSE dokłada do tego warstwę, która zamienia to w gesty CAD-a.

### Pełna separacja od zwykłej myszy

To jest główna zaleta tego deskryptora. Windows nie interpretuje kolekcji
*Multi-axis Controller*, więc urządzenie **nie rusza kursorem, nie przewija
i nie wpisuje znaków samo z siebie**. Wszystkim steruje aplikacja. W praktyce
oznacza to, że:

* gałka nie odbiera kursora Twojej zwykłej myszy — możesz pracować dwiema rękami,
* działa suwak czułości, bo to MAKMOUSE wykonuje ruch,
* nie trzeba niczego blokować, a to ważne: **zwrócenie 1 z hooka
  niskopoziomowego usuwa zdarzenie z całego potoku razem z raportem Raw Input**
  (zmierzone: klawisz przepuszczony → 6 raportów, zablokowany → 0). Blokowanie
  i rozpoznawanie urządzenia wzajemnie się wykluczają, więc każdy projekt oparty
  na blokadzie prędzej czy później się o to rozbija.

Konsekwencja, o której warto pamiętać: **bez uruchomionego MAKMOUSE urządzenie
nie robi nic.** To nie jest usterka, tylko cena separacji.

Aplikacja nie rejestruje też żadnej klawiatury w Raw Input i nie zakłada hooka
klawiatury — nie widzi ani jednego naciśnięcia klawisza w systemie.

Źródła wejścia są zakładane pod tryb, a nie raz na starcie. W trybie *Surowy HID*
aplikacja **nie zakłada hooka `WH_MOUSE_LL` i nie rejestruje kolekcji Mouse**
w Raw Input, więc zdarzenia zwykłej myszy nie przechodzą przez ani jedną linijkę
kodu MAKMOUSE. Ma to znaczenie praktyczne: hook niskopoziomowy jest wołany na
wątku, który go założył, więc sama jego obecność w procesie Pythona dokłada
opóźnienie do każdego ruchu każdej myszy w systemie. Hook wraca tylko wtedy, gdy
ręcznie przełączysz tryb na *Mysz* (dla starszego firmware'u).

### Gesty ciągłe (zakładka *Przyciski i gesty*)

Ruch gałki i obrót pierścienia nie mają „puszczenia" — jedynym sygnałem końca
gestu jest to, że przestały przychodzić zdarzenia. MAKMOUSE trzyma więc
modyfikator tak długo, jak trwa ruch, i zwalnia go po 250 ms ciszy.

Każdy ruch osi prowadzi *Navigator*: zapamiętuje pozycję wskaźnika przed gestem
i wykonuje przeciąganie (bo tylko tak program 3D zorbituje). Co się dzieje
z kursorem po geście, decyduje **pole *Zostaw kursor w nowym miejscu*** w zakładce
*Nawigacja 3D* — fabrycznie włączone, więc wskaźnik kończy tam, dokąd dojechał.
Po wyłączeniu wraca na pozycję sprzed gestu (zachowanie z wersji 1.3.1). Gdy
trzymany jest przycisk boczny, gest pozostaje otwarty aż do jego puszczenia.

**Modyfikator nie jest wymagany.** Pusty gest ruchu to pełnoprawne ustawienie:
gałka rusza wtedy kursorem tak jak zwykła mysz. Do 1.3.1 brak modyfikatora
blokował gest całkowicie i gałka była martwa wszędzie poza profilami z wpisanym
akordem orbity — to jest naprawione.

* **Ruch myszy + `Shift` i ŚPM** → orbita w Fusion 360 / Inventorze
  (to jest ustawienie domyślne obu profili CAD).
* **Ruch myszy bez modyfikatora** → zwykły ruch kursora.
* **Scroll + `Ctrl`** → zoom krokowy; można też `scroll + H` albo dowolny
  inny klawisz.

Gdy profil ma włączone **Sterowanie wprost (dodatek 3D)**, cała sekcja *Gesty
ciągłe* **znika** z zakładki — osie idą wtedy do dodatku i modyfikatory nie mają
żadnego wpływu.

W polach „co trzymać" (gesty ciągłe, gesty programu, akcja *Przytrzymaj
klawisze/przycisk*) wystarczy nacisnąć **sam modyfikator** — `Shift`, `Ctrl`,
`Alt`, `Win` albo ich kombinację. Klawisz główny nie jest wymagany; jeśli go
dodasz, zostanie zapamiętany razem z modyfikatorami. Pola przechwytujące pełne
skróty (np. *Skrót klawiszowy*) nadal wymagają klawisza głównego.

Scroll z modyfikatorem jest **przechwytywany i wysyłany ponownie** — inaczej
dotarłby do programu ułamek sekundy przed modyfikatorem i zadziałał jak zwykły
scroll. Blokada włącza się automatycznie tylko wtedy, gdy gest scrolla ma
przypisany modyfikator.

### Przyciski boczne

| Typ akcji | Zachowanie |
|---|---|
| Nic | przycisk przechodzi do systemu bez zmian |
| Nawigacja 3D | orbita / przesuwanie / zoom aktywne, dopóki trzymasz |
| Skrót klawiszowy | impuls przy naciśnięciu (np. `Ctrl+Z`) |
| Przytrzymaj klawisze/przycisk | trzyma kombinację do zwolnienia |

Wciśnięty przycisk boczny **wyłącza gest ruchu** — dzięki temu domyślny układ
działa tak: sam ruch orbituje, ruch z przyciskiem 1 (trzymane ŚPM) przesuwa
widok.

Każdy kafel ma **kwadracik w prawym górnym rogu**: wyłącza funkcję tego jednego
przycisku, zostawiając jego ustawienia nietknięte. Wyłączony przycisk przechodzi
do systemu bez zmian, a w legendzie podglądu jego kropka robi się czerwona.

---

## Profile

Profile przełączają się same według aktywnego programu (`.exe` z listy
w profilu). Fabrycznie jest ich siedem — **Fusion 360** (oznaczony jako domyślny,
więc obowiązuje też wszędzie tam, gdzie nie pasuje żaden inny), SolidCraft,
Inventor, Blender, SolidWorks, SketchUp i Rhino. Własne dodajesz przyciskiem
*Dodaj* albo *Duplikuj*.

**Kwadracik przy nazwie na liście** włącza i wyłącza cały profil — bez wchodzenia
w jego ustawienia. Wyłączony profil jest wyszarzony i nie bierze udziału
w dopasowaniu do aktywnego programu.

Do profilu należą: przypisania przycisków, gesty ciągłe, gesty programu,
sterowanie wprost **i cała sekcja osi X/Y** (od 1.3.2 — wcześniej czułości
i odwrócenia były wspólne dla całej aplikacji). Konfiguracja z 1.3.1 jest
przenoszona automatycznie: dotychczasowe ustawienia osi trafiają do każdego
profilu jako punkt wyjścia.

---

## Sterowanie wprost — dodatek do Fusion 360 (bez udziału kursora)

Emulacja myszy ma twardą granicę: żeby program 3D zorbitował, kursor **musi**
się przesunąć. Tak działa każde rozwiązanie oparte na przeciąganiu.

Profesjonalne manipulatory 3D omijają to inaczej — ich sterownik nie udaje myszy,
tylko podaje osie aplikacji, a ta sama przelicza kamerę. MAKMOUSE robi teraz to
samo dla Fusiona:
dodatek działający **wewnątrz** programu przestawia kamerę przez API, więc
kursor nie drga ani o piksel i można równolegle pracować zwykłą myszą.

```
MAKMOUSE (czyta HID)  --TCP 127.0.0.1:8765-->  dodatek w Fusion  -->  kamera
```

**Instalacja.** Źródło leży w [fusion_addin/MAKMOUSE/](fusion_addin/MAKMOUSE/);
kopię zainstalowano już w `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`.
W Fusionie: *Narzędzia → Dodatki (Scripts and Add-Ins) → Add-Ins → MAKMOUSE →
Run*, plus *Run on Startup*.

**Zachowanie.** Profil z polem `"direct": true` (domyślnie Fusion 360) wysyła osie
do dodatku. Gdy dodatek nie jest podłączony, profil **sam wraca** do emulacji
przeciągania — zamknięcie Fusiona nie unieruchamia gałki. Przycisk z akcją
*Nawigacja 3D* w tym trybie nie wciska niczego myszą, tylko przełącza tryb
w dodatku (np. orbita → przesuwanie).

## Sterowanie wprost — SolidCraft (bez dodatku do instalowania)

SolidCraft ma obsługę mostu wbudowaną w sam program, więc nie instaluje się
w nim żadnej wtyczki. Na razie jest ona tylko w lokalnej kompilacji SolidCrafta
(gałąź `makmouse-bridge`); oficjalne wydania SolidCrafta jej jeszcze nie mają —
dlatego w takiej kompilacji nie przyjmuj aktualizacji proponowanej przez sam
program, bo podmieni ją na oficjalną wersję.

```
MAKMOUSE (czyta HID)  --TCP 127.0.0.1:8765-->  SolidCraft  -->  kamera
```

1. W SolidCrafcie: *Preferencje → Nawigacja → Mysz 3D →* zaznacz **Nawiguj
   programem urządzenia na tym komputerze** (port `8765`, ten sam co
   `"bridge_port"` w konfiguracji MAKMOUSE). Obok pojawi się *Połączono · MAKMOUSE*.
2. W MAKMOUSE profil **SolidCraft** ma już *Sterowanie wprost* i na liście
   **Dodatek** wybrany *SolidCraft*. Dla własnego profilu zaznacz to samo.

Gałka orbituje (przycisk z akcją *Nawigacja 3D* przełącza na przesuwanie albo
zoom), pierścień przybliża, akcja *Widok (dodatek 3D)* ustawia widok standardowy.
W trakcie edycji szkicu widok się nie obraca — gałka go wtedy przesuwa. SolidCraft
sam też czyta myszy 3D przez HID; gdy MAKMOUSE jest podłączony mostem, SolidCraft
zostawia urządzenie o nazwie *MAKMOUSE* jemu, więc widok nie rusza się podwójnie.
Rusza się tylko okno SolidCrafta, które ma fokus.

Ograniczenie: sterowanie wprost działa w **Fusionie i SolidCrafcie**. Blender,
Rhino, SolidWorks czy Creo wymagają własnych wtyczek — każdy ma osobne API.
Protokół mostu jest jednak
wspólny, więc dodatek do kolejnego programu to głównie tłumaczenie tych samych
trzech komunikatów na jego API: **[ADDONS.md](ADDONS.md)** opisuje jak to zrobić,
z gotowym planem dla Creo Parametric.

Alternatywą pokrywającą wszystkie pakiety naraz byłoby podszycie się w firmwarze
pod komercyjny manipulator 3D (cudze VID/PID i sterownik jego producenta), co
jednak oznacza użycie cudzego identyfikatora producenta — MAKMOUSE tego nie robi.

---

## Nawigacja 3D — akcja „przytrzymaj tryb"

Gdy przycisk boczny ma akcję *Nawigacja 3D*, MAKMOUSE syntezuje pełny gest:

1. zapamiętuje pozycję kursora i (opcjonalnie) ustawia go na środku okna,
2. wciska modyfikatory i przycisk myszy zdefiniowane w profilu,
3. zamienia osie X/Y na ruch kursora **pozycją bezwzględną**, więc
   przyspieszenie wskaźnika Windows nie wpływa na wynik,
4. przy krawędzi ekranu **przepina gest** (puszcza przycisk, wraca na środek,
   wciska ponownie) — dzięki temu można obracać bez końca,
5. po zwolnieniu zwalnia wszystko i zostawia albo przywraca kursor — zależnie
   od pola *Zostaw kursor w nowym miejscu*.

Ten sam mechanizm prowadzi gest gałki, więc obsługa kursora dotyczy **każdego**
ruchu osi, nie tylko akcji przypisanej do przycisku. Dwa ustawienia — *Przepinaj
gest przy krawędzi* i *Kursor na środek okna przed gestem* — dotyczą wyłącznie
gestów, które coś trzymają (orbita, przesuwanie). Przy zwykłym ruchu kursora bez
modyfikatora są pomijane, bo byłyby tylko teleportacją na środek ekranu.

**Cała zakładka *Nawigacja 3D* należy do wybranego profilu** — każdy program ma
własne akordy, własne czułości i własne zachowanie kursora.

Domyślne gesty programu — akord orbity różni się między pakietami i to jedyne,
co realnie trzeba przestawiać. Wszystko jest edytowalne w UI:

| Program | Orbita | Przesuwanie | Zoom |
|---|---|---|---|
| Fusion 360 / Inventor | `Shift` + ŚPM | ŚPM | kółko |
| Blender | ŚPM | `Shift` + ŚPM | kółko |
| SolidWorks | ŚPM | `Ctrl` + ŚPM | kółko |
| SketchUp | ŚPM | `Shift` + ŚPM | kółko |
| Rhino | PPM | `Shift` + PPM | kółko |

Profil domyślny (catch-all) używa akordu Fusiona, bo `Shift` + ŚPM jest
najczęstszy — dzięki temu gałka działa też w programie, dla którego nie ma
jeszcze osobnego profilu.

### Czułość osi

Firmware zgłasza osie jako **przyrostowe** (`Relative`): każdy raport niesie
zmianę, a nie wychylenie. Wariant „wychylenie = prędkość" (jak w profesjonalnych
manipulatorach 3D) został usunięty — przy tym deskryptorze nie miał jak zadziałać,
a razem z nim zniknęły *martwa strefa* i *krzywa progresji*, które obsługiwały
wyłącznie jego.

Suwak *Czułość — ruch gałki* skaluje sam ruch gałki. Dwa dolne (*orbita*,
*przesuwanie*) obowiązują wtedy, gdy przycisk boczny trzyma akcję *Nawigacja 3D* —
także jako przełącznik. Przykład: przycisk 1 ustawiony na *Nawigacja 3D →
Przesuwanie* z zaznaczonym przełącznikiem przestawia gałkę na przesuwanie i od tej
chwili osie idą z *Czułością — przesuwanie*, niezależnie od *Czułości — ruch gałki*;
po ponownym wciśnięciu wracają do niej.

**Wszystkie działają tak samo w obu ścieżkach** — przez dodatek w Fusionie i przez
emulację przeciągania. (W 1.3.2 w kanale do dodatku osie zawsze dostawały czułość
ruchu gałki, więc orbita i przesuwanie nie miały tam własnego tempa — to jest
poprawione.)

**Czułość — zoom (pierścień)** to **skok jednego kliknięcia**, wartości od 0,1 do
5,0 co 0,1. Liczba kliknięć się nie zmienia — pierścień dalej daje 20 na obrót —
zmienia się to, jak daleko przesuwa go jedno kliknięcie:

| wartość | co robi jedno kliknięcie |
|---|---|
| 0,3 | trzykrotnie drobniej: mniej wierszy na stronie, bliższe podejście do bryły |
| 1,0 (fabrycznie) | tyle, co zwykły klik kółka myszy |
| 2,5 | dwa i pół raza większy skok |

Ta sama wartość obowiązuje w obu miejscach, w których dzieje się zoom: pierścień
w zwykłym programie (skalowany `WHEEL_DELTA`, czyli mniej przewiniętych wierszy)
i kamera w programie 3D (krótszy skok przybliżenia — przez dodatek albo przez akcję
*Nawigacja 3D → Zoom*). Dlatego jest jeden suwak, a nie osobny dla każdej ścieżki.

> Bardzo małe wartości (0,1–0,2) wysyłają ułamek standardowego kliknięcia kółka.
> Współczesne programy (przeglądarki, Fusion, Office) sumują takie zdarzenia
> poprawnie; pojedyncze stare aplikacje, które dzielą `WHEEL_DELTA` bez reszty,
> mogą je pominąć — wtedy wystarczy podnieść wartość.

---

## Akcje przycisków bocznych

| Typ | Działanie |
|---|---|
| Nic | przycisk przechodzi dalej bez zmian |
| Nawigacja 3D | orbita / przesuwanie / zoom na czas przytrzymania |
| Skrót klawiszowy | wysyłany raz przy naciśnięciu |
| Przytrzymaj klawisze/przycisk | trzymane aż do puszczenia |
| **Widok (dodatek 3D)** | ustawia widok: przód, tył, lewo, prawo, góra, dół, izometria, dopasuj |

*Widok (dodatek 3D)* idzie mostem do dodatku programu wybranego w profilu (Fusion
albo SolidCraft), więc pojawia się **tylko w profilu z włączonym sterowaniem
wprost** — w pozostałych nie ma go na liście, bo nie miałby jak zadziałać.

### Przełącznik

Każda akcja, która coś utrzymuje (*Nawigacja 3D*, *Przytrzymaj*), może działać
jako **przełącznik**: pierwsze wciśnięcie włącza, drugie wyłącza — puszczenie
przycisku niczego nie gasi. Typowe zastosowanie: przycisk przestawia gałkę
z orbity na przesuwanie bryły i zostawia ją tak do kolejnego kliknięcia.

---

## Tryb odczytu

Urządzenie zgłasza się jako *Multi-axis Controller* i raportuje układem
ustalonym w firmware (raport ID 1, 5 bajtów). Nie ma tu nic do wybierania, więc
zakładka *Urządzenie* pokazuje już tylko wykryty sprzęt. Windows nie interpretuje
tej kolekcji, więc kursorem, scrollem i przyciskami steruje wyłącznie MAKMOUSE.

---

## Rozwiązywanie problemów

**„MAKMOUSE — Nieaktywny".** Deskryptor USB nie zawiera tej nazwy albo
urządzenie nie jest podpięte. Sprawdź `iProduct`/`iManufacturer` w firmware
i kliknij *Szukaj ponownie* w zakładce *Urządzenie*.

**Przycisk boczny nic nie robi.** Otwórz *Monitor* i naciśnij go. Jeśli surowe
bajty raportu się zmieniają, ale nie ma linii „przycisk boczny N DOŁ", to znaczy,
że firmware wysyła inny układ raportu niż ustalony (raport ID 1, przyciski w
bajcie 4). Jeśli nie zmienia się nic, sprawdź czy urządzenie jest *Aktywne*.

**Ruch albo scroll idzie w złą stronę.** *Odwróć X* / *Odwróć Y* w zakładce
*Nawigacja 3D*; dla pierścienia (scroll i zoom) zaznacz tam *Odwróć zoom*.

**Scroll nie przybliża w Fusionie.** Fusion domyślnie renderuje kamerą
**ortograficzną**, w której przesunięcie oka nie zmienia obrazu — skalę widoku
trzyma `viewExtents`. Dodatek rozpoznaje typ kamery i rusza właściwym polem.

**Gałka działa, ale zmiana czułości nic nie daje w Fusionie.** Upewnij się, że
profil Fusiona ma zaznaczone *Sterowanie wprost* i że podgląd pokazuje
*Dodatek podłączony*.

**Nie działa nad oknem uruchomionym jako administrator.** Hooki niskopoziomowe
nie przechwycą wejścia idącego do procesu o wyższym poziomie integralności.
Uruchom MAKMOUSE jako administrator (Fusion 360 i Inventor tego nie wymagają).

**Coś się zacięło.** Skrót awaryjny (domyślnie `Ctrl+Alt+F12`) zwalnia wszystkie
trzymane klawisze i przełącza MAKMOUSE w stan wyłączony.

---

## Struktura projektu

Pełny opis kodu — co robi każdy plik, jak płyną dane, wątki, gdzie szukać przy
zmianach — jest w **[STRUKTURA.md](STRUKTURA.md)**. Skrót:

```
run.py                  uruchomienie aplikacji + przebudowa okna po zmianie języka
build_exe.bat           generowanie gotowego .exe (jeden plik albo folder)
build_installer.bat     generowanie instalatora MAKMOUSE-<wersja>-setup.exe jednym kliknięciem
MAKMOUSE-onefile.spec   przepis PyInstallera - jeden plik dist\MAKMOUSE.exe
MAKMOUSE.spec           przepis PyInstallera - folder dist\MAKMOUSE\ (dla instalatora)
Program instalacyjny (exe)/
  MAKMOUSE.iss          skrypt Inno Setup; gotowe instalatory lądują w Output\
makmouse/
  i18n.py               słownik tłumaczeń PL/EN i funkcja tr()
  winapi.py             struktury i prototypy Win32 (ctypes)
  devices.py            wyliczanie urządzeń, odczyt nazw z deskryptora USB
  engine.py             wątek silnika: Raw Input + hooki + parowanie strumieni
  output.py             SendInput: klawiatura (scancode), przyciski, ruch, scroll
  navigator.py          osie X/Y -> gesty orbit/pan/zoom, przepinanie przy krawędzi
  profiles.py           model konfiguracji, profile, zapis/odczyt JSON
  appwatch.py           wykrywanie aktywnego programu
  controller.py         spięcie silnika, profili i akcji; gesty ciągłe
  keys.py               nazwy klawiszy <-> kody wirtualne, parsowanie skrótów
  ui/
    theme.py            motyw jasny/ciemny, 10 kolorów wiodących, zasoby
    device_view.py      rysowana grafika 3D urządzenia — podgląd na żywo
    widgets.py          karty, przełączniki, przechwytywanie skrótów, wskaźniki
    help_dialog.py      instrukcja obsługi otwierana przyciskiem „i"
    main_window.py      okno główne
fusion_addin/           dodatek do Fusion 360 (SolidCraft ma obsługę mostu wbudowaną)
```

---

## Budowanie pliku .exe

Najprościej: **kliknij dwukrotnie [build_exe.bat](build_exe.bat)**. Skrypt sam
sprawdza Pythona, doinstalowuje `PySide6` i `pyinstaller`, jeśli ich nie ma,
buduje program i zostawia gotowy plik:

```
Program gotowy (bez instalatora)\MAKMOUSE.exe
```

To **jeden plik ~36 MB**, który można skopiować na pendrive i uruchomić na innym
komputerze bez instalowania czegokolwiek. Kolejne uruchomienia skryptu nadpisują
poprzednią wersję — nic nie trzeba sprzątać ręcznie.

Są dwa warianty:

| polecenie | wynik | uwagi |
|---|---|---|
| `build_exe.bat` | `Program gotowy (bez instalatora)\MAKMOUSE.exe` | jeden plik, start ~3–5 s (rozpakowanie do folderu tymczasowego) |
| `build_exe.bat folder` | `Program gotowy (bez instalatora)\MAKMOUSE\MAKMOUSE.exe` + `_internal\` | wiele plików, start natychmiastowy; tego wariantu używa instalator |

Ręcznie, bez skryptu, to dokładnie to samo co:

```powershell
python -m pip install pyinstaller PySide6
python -m PyInstaller --noconfirm --clean MAKMOUSE-onefile.spec   # jeden plik
python -m PyInstaller --noconfirm --clean MAKMOUSE.spec           # wersja folderowa
```

Oba przepisy ustawiają `console=False` (aplikacja mieszka w zasobniku i nie
wypisuje nic na stdout), podpinają ikonę `makmouse.ico` i wycinają nieużywane
moduły Qt — bez tego paczka rośnie o kilkaset megabajtów QtWebEngine i QtQuick.

Foldery `build\` i `dist\` to robocze wyjście PyInstallera; można je kasować
w dowolnym momencie.

Aplikacja jest wyłącznie dla Windows (Raw Input, hooki LL, `SendInput`), więc
exe trzeba zbudować na Windows i na tej samej architekturze co docelowa.
Przenoszenie gotowej paczki na inny komputer opisuje [INSTALL.md](INSTALL.md).

---

## Numeracja wersji

Wersja żyje w jednym miejscu — `makmouse/__init__.py` — i stamtąd trafia do
tytułu okna, paska górnego, zasobnika i instrukcji. Schemat `1.x.x`:

* **1.x.0** — nowa funkcja albo zmiana zachowania,
* **1.x.y** — poprawka bez zmiany zachowania.
