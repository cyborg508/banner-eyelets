# banner-eyelets web — design spec

**Data:** 2026-06-12  
**Status:** zatwierdzone

## Cel

Port aplikacji desktopowej banner-eyelets na serwis webowy hostowany na drukpolu (TrueNAS SCALE), dostępny publicznie przez `https://banner.cyplos.pl` via Cloudflare Tunnel. Pełna parność funkcjonalna z desktopem. Wygląd zgodny ze stylem summa-cut.

---

## Struktura projektu

```
~/banner-eyelets/
├── banner_eyelets/          # nowy pakiet — czysta logika, zero PySide6
│   ├── __init__.py
│   ├── geometry.py          # evenly_spaced_positions, build_eyelet_points, cm_to_pt, pt_to_cm
│   ├── pdf_ops.py           # draw_cross, draw_frame, generate_annotated_pdf
│   └── models.py            # BannerSpec, RenderConfig, DEFAULT_SETTINGS
├── app.py                   # desktop — bez zmian w zachowaniu, importuje z banner_eyelets/
├── web/
│   ├── __init__.py
│   ├── server.py            # FastAPI app
│   ├── sessions.py          # lekki SessionStore (dict + tmpfile + TTL)
│   └── static/
│       ├── index.html
│       ├── app.js
│       └── style.css
├── Dockerfile
├── compose.yaml             # port hosta 8801 → 8000 w kontenerze
├── requirements.txt         # PySide6 + PyMuPDF (desktop)
├── requirements-web.txt     # fastapi uvicorn python-multipart PyMuPDF
└── tests/
    └── test_geometry.py     # unit testy czystej logiki (bez Qt, bez serwera)
```

Logika wyodrębniona z `app.py` do pakietu `banner_eyelets/`. Desktop `app.py` importuje z pakietu — zachowanie identyczne. Kontener webowy nie zawiera PySide6.

---

## Backend API

Serwer: FastAPI (`web/server.py`), uruchamiany przez uvicorn.

### Endpointy

| Endpoint | Metoda | Wejście | Wyjście |
|---|---|---|---|
| `/` | GET | — | `index.html` |
| `/api/upload` | POST | plik PDF (multipart) | `{sid, width_cm, height_cm}` |
| `/api/preview` | GET | `sid` + params (query) | `image/png` |
| `/api/generate` | GET | `sid` + params (query) | `application/pdf` (attachment) |

### Parametry query (`/api/preview`, `/api/generate`)

`out_w`, `out_h`, `margin`, `spacing`, `marker`, `border` (bool), `wrap` (bool), `half` (bool), `wrap_extra`

`sid` przychodzi z **cookie** `sid` (ustawianego przez `/api/upload`) — browser wysyła je automatycznie przy `img.src` i `window.location.href`, bez jawnego dołączania do URL.

### Sesja (`web/sessions.py`)

- Dict `{sid: {path: Path, created: float}}`
- `sid` = UUID4, ustawiany jako cookie `sid` (httponly, samesite=lax) przez endpoint `/api/upload`
- `sweep(max_age_hours=2)` wywoływane w `lifespan` przy starcie (usuwa stare tmpfile)
- Tmpfile tworzone w katalogu `SESSIONS_DIR` (env `BANNER_SESSIONS_DIR`, domyślnie `/tmp/banner-eyelets-web`)

### `generate_annotated_pdf(src_path, spec, render_cfg) → bytes`

Czysta funkcja w `banner_eyelets/pdf_ops.py`. Tworzy docelowy PDF w pamięci (`fitz.open()`), osadza wejściowy PDF wycentrowany, rysuje ramki (jeśli border/wrap), rysuje krzyżyki. Zwraca bytes. Używana przez oba endpointy.

`/api/preview` rasteryzuje stronę 0 uzyskanego PDF do PNG przez `page.get_pixmap()`. Maks. szerokość podglądu: 900 px.

---

## Frontend

Plik: `web/static/{index.html, app.js, style.css}`

### Układ (dwukolumnowy)

```
┌─────────────────────────────────────────────────────┐
│  Banner Eyelets                                      │
├────────────────────────┬────────────────────────────┤
│  [Drag & drop / Otwórz]│                            │
│  ─────────────────────  │   <img id="preview">       │
│  Informacje             │   (podgląd z krzyżykami)   │
│  Wymiary                │                            │
│  Oczka                  │                            │
│  Opcje                  │                            │
│  ─────────────────────  │                            │
│  [Generuj PDF z oczkami]│                            │
│  ─────────────────────  │                            │
│  ▼ Podgląd punktów      │                            │
│  1. x=1.50 y=1.50 cm   │                            │
│  2. x=51.50 y=1.50 cm  │                            │
│  ...                    │                            │
└────────────────────────┴────────────────────────────┘
```

### Sekcje lewej kolumny

**Informacje** (read-only po uploadzie): nazwa pliku, liczba stron, wymiar z PDF.

**Wymiary:**
- Wejście szer. / wys. [cm] — read-only (z PDF)
- Wyjście szer. / wys. [cm] — edytowalne (pre-fill z PDF)

**Oczka:**
- Margines oczek [cm] — domyślnie 1.5
- Docelowy odstęp [cm] — domyślnie 50.0
- Rozmiar krzyżyka [cm] — domyślnie 1.0

**Opcje:**
- Checkbox Obramówka
- Checkbox Zawinięcie → po zaznaczeniu pojawia się pole „Zawinięcie na stronę [cm]" (domyślnie 3.0) + automatycznie zaznacza Obramówka
- Checkbox 50%

**Przyciski:**
- Otwórz PDF (alternatywa dla drag & drop)
- Generuj PDF z oczkami

**Podgląd punktów:** zwijana sekcja poniżej przycisków, lista `N. x=X.XX cm, y=Y.YY cm`. Liczona w JS (port algorytmu `evenly_spaced_positions` + `build_eyelet_points`, ~25 linii), bez round-tripu do serwera. Nagłówek sekcji pokazuje liczbę oczek.

### Zachowanie JS

- Upload (drag & drop lub dialog) → `POST /api/upload` → uzupełnia pola wymiarów, odblokowuje formularz (cookie `sid` ustawiane przez serwer)
- Zmiana dowolnego parametru → debounce 400 ms → `img.src = '/api/preview?params'` → przeglądarka wysyła cookie automatycznie
- Checkbox Zawinięcie → toggle pola wrap_extra + force-check Obramówka
- Przycisk Generuj → `window.location.href = '/api/generate?params'` → przeglądarka wysyła cookie automatycznie → pobranie pliku
- Podgląd punktów → toggle sekcji, przelicza listę w JS

### Wygląd

Styl identyczny z summa-cut: `style.css` summa-cut jako baza (grafit `#1a1a2e` / `#16213e`, akcent zielony, monospace dla liczb, karty sekcji, focus-visible). Globalne `[hidden] { display: none !important; }` (zapobiega nadpisaniu przez flexbox).

---

## Docker i wdrożenie

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements-web.txt .
RUN pip install -r requirements-web.txt
COPY banner_eyelets/ ./banner_eyelets/
COPY web/ ./web/
EXPOSE 8000
CMD ["uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### compose.yaml

```yaml
services:
  banner-eyelets-web:
    build: .
    image: banner-eyelets-web:local
    container_name: banner-eyelets-web
    restart: unless-stopped
    ports:
      - "8801:8000"
    volumes:
      - banner-eyelets-data:/tmp/banner-eyelets-web
    environment:
      - BANNER_SESSIONS_DIR=/tmp/banner-eyelets-web
    networks: [proxy]

volumes:
  banner-eyelets-data:

networks:
  proxy:
    name: proxy-net
    external: true
```

### Caddyfile (~/drukpol-proxy/Caddyfile)

Dodanie bloku:
```
banner.cyplos.pl {
    import cf_tls
    reverse_proxy banner-eyelets-web:8000
}
```

### Cloudflare Tunnel

Dodanie reguły ingress w konfiguracji tunelu `drukpol` (`REDACTED-TUNNEL-ID`):
```
banner.cyplos.pl → https://caddy:443  (originServerName: banner.cyplos.pl)
```

### DNS Cloudflare (cyplos.pl)

Rekord: `banner CNAME REDACTED-TUNNEL-ID.cfargotunnel.com` — proxied (jak summa.cyplos.pl).

### Procedura aktualizacji

```bash
rsync -az --delete --exclude .venv --exclude .git --exclude __pycache__ \
  ~/banner-eyelets/ root@REDACTED-HOST:/srv/app/
ssh root@REDACTED-HOST 'docker build -t banner-eyelets-web:local \
  /srv/app && midclt call app.redeploy banner-eyelets'
```

---

## Testy

`tests/test_geometry.py` — unit testy `banner_eyelets/geometry.py` bez Qt i bez serwera:
- `evenly_spaced_positions` (przypadki graniczne: inner=0, niedziałający podział)
- `build_eyelet_points` (weryfikacja narożników, unikalność, symetria)
- `cm_to_pt` / `pt_to_cm` round-trip

`tests/test_web.py` — integracyjne przez `TestClient` (FastAPI):
- `POST /api/upload` z fixture PDF → 200, zwraca wymiary
- `GET /api/preview` z poprawnymi/nieprawidłowymi params → 200/400
- `GET /api/generate` → nagłówek `Content-Disposition: attachment`

---

## Czego NIE ma w tym spec (świadome pominięcia)

- Preferences dialog / persystencja ustawień — wszystkie parametry na głównym formularzu, reset przy odświeżeniu strony
- Autentykacja — serwis publiczny bez logowania (jak summa.cyplos.pl)
- Multi-user isolation — sesje rozróżniane przez sid, brak auth; wystarczające dla narzędzia produkcyjnego
- Rate limiting — nie w pierwszej wersji
