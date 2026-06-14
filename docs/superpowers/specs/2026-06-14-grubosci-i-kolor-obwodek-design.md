# Sterowanie grubością linii i kolorem obwódek — design

Data: 2026-06-14

## Cel
Dodać do web UI kontrolę grubości linii ramek i krzyżyków oraz wybór koloru
otoczki ramki.

## Model rysowania
Ramka (`draw_frame`, używana w Obramówce i obu ramkach Zawinięcia) oraz krzyżyk
(`draw_cross`) rysowane są jako **kolorowa otoczka (halo) + czarna linia konturu**.

Nazewnictwo ze specyfikacji:
- **granica obrysu** = czarna linia konturu ramki
- **obwódka** = kolorowa otoczka (halo) wokół tej linii

## Nowe kontrolki UI
| Kontrolka | Jedn. | Default | Działanie |
|---|---|---|---|
| Grubość granicy obrysu | mm | 1.0 | grubość czarnej linii ramki |
| Grubość obwódki | mm | 1.0 | szerokość otoczki po KAŻDEJ stronie linii (halo = linia + 2×obwódka) |
| Kolor obwódki | wybór | szary | czarny / biały / C / M / Y / szary |
| Grubość krzyżyków | mm | 1.2 | grubość linii krzyżyka (75% obecnej ~1.6mm); otoczka = 2×linia, biała |

## Decyzje
1. 75% krzyżyka liczone od czarnej linii (~1.6mm przy markerze 1cm → 1.2mm).
2. Kolor dotyczy otoczki ramki (dotąd biała → domyślnie szara). Krzyżyki bez zmian koloru.
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
