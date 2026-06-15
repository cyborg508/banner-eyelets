# Skalowanie grafiki PDF — design

Data: 2026-06-15

## Cel
Dodać między „Wejście" a „Wyjście" możliwość skalowania wczytanej grafiki PDF:
przez podanie wymiaru (cm), procentowo oraz z blokadą proporcji.

## Model
Grafika PDF jest dziś rysowana w rozmiarze **wejścia**, wyśrodkowana w arkuszu
**wyjścia** (`target_rect` w `generate_annotated_pdf`). Skalowanie zmienia rozmiar
rysowanej grafiki na **rozmiar skalowania**; nadal wyśrodkowana w wyjściu.

- Oczka i ramka liczone dalej od **Wyjścia** (bez zmian).
- „Wyjście" pozostaje osobnym polem (arkusz; default = rozmiar PDF).
- Default: skala = wejście (100%) → wynik identyczny jak dotąd (wstecznie zgodne).
- Skalowana grafika większa od wyjścia → przycięcie (istniejące ostrzeżenie).

## UI — nowa sekcja „Skalowanie"
| Kontrolka | Działanie |
|---|---|
| Szerokość [cm] | docelowa szerokość grafiki |
| Wysokość [cm] | docelowa wysokość grafiki |
| Skala [%] | mnożnik względem wejścia (100% = wejście) |
| ☑ Proporcjonalnie (default ON) | wiąże szerokość z wysokością |

Logika (JS):
- Po wczytaniu: W=wejście.szer, H=wejście.wys, %=100, Proporcjonalnie ON.
- Proporcjonalnie ON: edycja %/W/H przelicza pozostałe wg proporcji wejścia.
- Proporcjonalnie OFF: W i H niezależne; pole % nieaktywne.

## Zmiany w kodzie
- `banner_eyelets/pdf_ops.py`:
  - nowy helper `centered_rect(left, top, region_w, region_h, content_w, content_h)`
  - `generate_annotated_pdf`: opcjonalne `artwork_width_cm` / `artwork_height_cm`
    (None → wymiary wejścia), użyte do `target_rect` przez `centered_rect`.
- `web/server.py`: query params `scale_w` / `scale_h` (cm); None → wymiary wejścia z sesji.
- `web/static/index.html` + `app.js`: sekcja „Skalowanie" + logika %↔cm↔proporcja,
  inicjalizacja po uploadzie, przekazanie `scale_w`/`scale_h`.
- `tests/`: `centered_rect`, skalowanie grafiki (render), web params.

## Decyzje
1. Skala dotyczy tylko grafiki (nie zmienia arkusza ani oczek).
2. Baza % = wejście (100% = oryginał PDF).
3. Proporcjonalnie OFF → % wyłączone, sterowanie W i H w cm.
