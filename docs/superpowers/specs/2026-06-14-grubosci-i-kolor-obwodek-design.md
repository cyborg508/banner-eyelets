# Sterowanie grubością linii i kolorem obwódek — design

Data: 2026-06-14

## Cel
Dodać do web UI kontrolę grubości linii ramek i krzyżyków oraz wybór koloru
otoczki ramki.

## Model rysowania
**Obramówka (`draw_frame`, w Obramówce i obu ramkach Zawinięcia) = JEDNA linia** w
zadanym kolorze i grubości (bez otoczki, bez czarnej linii na wierzchu).

Krzyżyki (`draw_cross`) pozostają **znacznikami**: czarna linia w białej otoczce
(kontrast na każdym tle) — reguluje się tylko ich grubość, kolor obramówki ich nie dotyczy.

Doprecyzowanie po pierwszej iteracji: „obwódka" i „granica obrysu" to ta sama,
pojedyncza linia obramówki (jedno pole grubości), nie halo+kontur.

## Nowe kontrolki UI
| Kontrolka | Jedn. | Default | Działanie |
|---|---|---|---|
| Grubość obramówki | mm | 1.0 | grubość pojedynczej linii obramówki/zawinięcia |
| Kolor obramówki | wybór | szary | szary / czarny / biały / C / M / Y |
| Grubość krzyżyków | mm | 1.2 | grubość linii krzyżyka (75% dotychczasowej ~1.6mm); otoczka = 2×linia, biała |

## Decyzje
1. 75% krzyżyka liczone od czarnej linii (~1.6mm przy markerze 1cm → 1.2mm).
2. Obramówka = pojedyncza linia w wybranym kolorze (default szary). Krzyżyki bez zmian (czarne w białej otoczce).
3. C/M/Y = prawdziwy CMYK (cyan=(1,0,0,0) itd.); szary = (0.5,0.5,0.5); biały=(1,1,1); czarny=(0,0,0).
4. Nowe grubości skalują się przy 50% (parametry technologiczne).
5. Zmiana w web UI + wspólnym `pdf_ops`; sygnatury wstecznie kompatybilne (desktop `app.py` bez zmian).

## Pliki
- `banner_eyelets/geometry.py` — `mm_to_pt`
- `banner_eyelets/models.py` — nowe defaulty
- `banner_eyelets/pdf_ops.py` — `draw_frame`/`draw_cross` + przekazanie param. w `generate_annotated_pdf`
- `web/server.py` — nowe query params (preview/generate) + skalowanie 50%
- `web/static/index.html`, `web/static/app.js` — kontrolki
- `tests/` — testy jednostkowe i web
