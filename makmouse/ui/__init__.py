"""Interfejs graficzny MAKMOUSE (PySide6 / Qt).

ZA CO ODPOWIADA
    Wszystko, co widać na ekranie. Logika urządzenia jest poza tym folderem -
    okno tylko pokazuje stan i zmienia konfigurację.

ZAWARTOŚĆ
    main_window.py .... okno główne: profile, podgląd, zakładki, zasobnik
    widgets.py ........ własne kontrolki (karty, przełączniki, kafle przycisków, ...)
    device_view.py .... rysowana grafika urządzenia - podgląd na żywo
    theme.py .......... kolory, motyw jasny/ciemny, kolor wiodący, ikona
    help_dialog.py .... instrukcja obsługi pod przyciskiem "i"
"""
