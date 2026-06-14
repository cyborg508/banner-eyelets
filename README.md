# banner-eyelets

Generator znaczników pod **oczka** na banery. Wczytuje jednostronicowy PDF, rozmieszcza równomiernie oczka po obwodzie i zapisuje nowy PDF z krzyżykami (znacznikami) — opcjonalnie z obramówką, zawinięciem i parametrami technologicznymi.

Dostępny w dwóch wariantach z tej samej logiki:

- 🖥️ **Desktop** (PySide6 + PyMuPDF) — aplikacja okienkowa, build portable na Windows.
- 🌐 **Web** (FastAPI + PyMuPDF) — podgląd na żywo w przeglądarce.

**Demo:** https://banner.cyplos.pl

---

## Jak to działa

1. Wczytujesz jednostronicowy PDF (przeciągnij i upuść albo wybierz plik).
2. Program odczytuje wymiar strony; możesz nadpisać wymiar wyjściowy w cm.
3. Oczka rozmieszczane są **równomiernie na każdym boku** (narożniki w stałym marginesie), z docelowym odstępem zaokrąglanym do pełnej liczby segmentów.
4. W każdym punkcie rysowany jest **krzyżyk** — czarna linia w białej otoczce (czytelny na każdym tle).
5. Zapisujesz gotowy PDF z naniesionymi znacznikami.

## Funkcje

- Wczytywanie PDF (drag & drop / wybór pliku), odczyt wymiaru strony
- Ręczne nadpisanie wymiaru wyjściowego w cm
- Równomierne rozmieszczenie oczek na obwodzie + margines narożny
- **Krzyżyki** jako znaczniki — regulowana grubość linii [mm]
- **Obramówka** — pojedyncza linia o zadanej grubości [mm] i kolorze
- **Kolor obramówki**: szary / czarny / biały / **C / M / Y** (prawdziwy CMYK)
- **Zawinięcie** — dodatek na stronę + zewnętrzna ramka
- **Tryb 50%** — zmniejsza dodatki technologiczne o połowę przy zachowaniu wymiaru wyjściowego
- Web: **podgląd na żywo** (debounce) + lista wyliczonych punktów oczek
- Generowanie PDF gotowego do druku

## Architektura

Czysta logika oddzielona od interfejsów (zero zależności od Qt/FastAPI w rdzeniu):

```
banner_eyelets/      # rdzeń, czysta logika
  geometry.py        #   przeliczenia jednostek, rozmieszczanie punktów
  pdf_ops.py         #   rysowanie krzyżyków/ramki, generowanie PDF
  models.py          #   BannerSpec, RenderConfig, ustawienia domyślne
app.py               # interfejs desktop (PySide6)
web/                 # interfejs web (FastAPI)
  server.py          #   API: /api/upload, /api/preview (PNG), /api/generate (PDF)
  sessions.py        #   sesje plikowe z TTL (cookie `sid`)
  static/            #   index.html + app.js + style.css
tests/               # testy (pytest)
```

---

## Web

### Lokalnie

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-web.txt
uvicorn web.server:app --reload
```

Aplikacja: http://127.0.0.1:8000

### Docker

```bash
docker compose up --build
```

Domyślnie wystawia port `8801` → `8000` w kontenerze (zob. `compose.yaml`). Sesje trzymane są w katalogu wskazanym przez `BANNER_SESSIONS_DIR`.

---

## Desktop

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Build portable na Windows

```bat
build-windows-portable.bat
```

Wynik (cały folder do przeniesienia): `dist\BannerEyelets\` z plikiem `BannerEyelets.exe`. Szczegóły w [`WINDOWS_PORTABLE.md`](WINDOWS_PORTABLE.md).

---

## Testy

```bash
pip install -r requirements-dev.txt -r requirements-web.txt
pytest
```

## Stack

Python 3.12 · [PyMuPDF](https://pymupdf.readthedocs.io/) (rdzeń PDF) · [PySide6](https://doc.qt.io/qtforpython/) (desktop) · [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) (web)
