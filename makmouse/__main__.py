"""Alternatywne uruchomienie: `python -m makmouse`.

ZA CO ODPOWIADA
    * dopisuje katalog projektu do ścieżki importów i woła run.main() - dzięki
      temu program startuje tak samo jak przez `python run.py`.

POWIĄZANIA
    Cała logika startu jest w run.py; ten plik jest tylko przekierowaniem.
"""
from __future__ import annotations

import sys

if __name__ == "__main__":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from run import main

    sys.exit(main())


