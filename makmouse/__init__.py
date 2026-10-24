"""Pakiet MAKMOUSE CAD Software - sterownik myszy 3D MAKMOUSE dla programów CAD.

ZA CO ODPOWIADA
    * jedno źródło numeru wersji (__version__) - stąd biorą go tytuł okna, pasek
      górny, zasobnik, instrukcja i skrypt instalatora (.iss odczytuje go
      stąd sam); przy wydaniu zmienia się go tylko tutaj,
    * nazwa aplikacji (APP_NAME) używana w oknach i komunikatach.

POWIĄZANIA
    Logika programu leży w modułach obok, okno w podpakiecie ui/.
    Punkt startowy całej aplikacji: run.py w katalogu projektu.
"""

__version__ = "1.4.1"
APP_NAME = "MAKMOUSE CAD Software"
