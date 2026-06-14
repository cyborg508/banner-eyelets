from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import fitz
from fastapi import Cookie, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from banner_eyelets.geometry import mm_to_pt
from banner_eyelets.models import BannerSpec, RenderConfig
from banner_eyelets.pdf_ops import frame_color_tuple, generate_annotated_pdf
from web.sessions import SessionStore

PREVIEW_MAX_PX = 900


def build_render_config(
    out_w: float,
    out_h: float,
    margin: float,
    spacing: float,
    marker: float,
    wrap: bool,
    half: bool,
    wrap_extra: float,
) -> RenderConfig:
    factor = 0.5 if half else 1.0
    scaled_wrap = (wrap_extra * factor) if wrap else 0.0
    return RenderConfig(
        scaled_margin_cm=margin * factor,
        scaled_spacing_cm=spacing * factor,
        scaled_marker_size_cm=marker * factor,
        scaled_wrap_cm=scaled_wrap,
        final_width_cm=out_w + 2 * scaled_wrap,
        final_height_cm=out_h + 2 * scaled_wrap,
    )


def build_marker_kwargs(
    half: bool,
    frame_mm: float,
    frame_color: str,
    cross_mm: float,
) -> dict:
    """Grubości w mm → punkty (ze skalą 50% jak inne parametry technologiczne)."""
    factor = 0.5 if half else 1.0
    return {
        "frame_line_width_pt": mm_to_pt(frame_mm * factor),
        "frame_color": frame_color_tuple(frame_color),
        "cross_line_width_pt": mm_to_pt(cross_mm * factor),
    }


def create_app(store: SessionStore) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        store.sweep()
        yield

    app = FastAPI(title="banner-eyelets web", lifespan=lifespan)

    _static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_static / "index.html")

    @app.post("/api/upload")
    async def upload(file: UploadFile = File(...)) -> Response:
        data = await file.read()
        if data[:4] != b"%PDF":
            raise HTTPException(400, "Plik nie jest PDF.")
        sid, width_cm, height_cm, page_count = store.create(data)
        body = json.dumps({
            "sid": sid,
            "width_cm": round(width_cm, 4),
            "height_cm": round(height_cm, 4),
            "page_count": page_count,
        })
        resp = Response(content=body, media_type="application/json")
        resp.set_cookie("sid", sid, httponly=True, samesite="lax")
        return resp

    def _require_session(sid: str | None) -> dict:
        if not sid:
            raise HTTPException(401, "Brak sesji.")
        entry = store.get(sid)
        if entry is None:
            raise HTTPException(401, "Sesja wygasła lub nie istnieje.")
        return entry

    def _common_params(
        sid: str | None,
        out_w: float,
        out_h: float,
        margin: float,
        spacing: float,
        marker: float,
        border: bool,
        wrap: bool,
        half: bool,
        wrap_extra: float,
    ) -> tuple[dict, BannerSpec, RenderConfig]:
        entry = _require_session(sid)
        spec = BannerSpec(
            input_width_cm=entry["width_cm"],
            input_height_cm=entry["height_cm"],
            output_width_cm=out_w,
            output_height_cm=out_h,
            margin_cm=margin,
            target_spacing_cm=spacing,
            marker_size_cm=marker,
        )
        render_cfg = build_render_config(out_w, out_h, margin, spacing, marker, wrap, half, wrap_extra)
        return entry, spec, render_cfg

    @app.get("/api/preview")
    def preview(
        sid: str | None = Cookie(default=None),
        out_w: float = 100.0,
        out_h: float = 100.0,
        margin: float = 1.5,
        spacing: float = 50.0,
        marker: float = 1.0,
        border: bool = False,
        wrap: bool = False,
        half: bool = False,
        wrap_extra: float = 3.0,
        frame_mm: float = 1.0,
        frame_color: str = "gray",
        cross_mm: float = 1.2,
    ) -> Response:
        entry, spec, render_cfg = _common_params(
            sid, out_w, out_h, margin, spacing, marker, border, wrap, half, wrap_extra
        )
        pdf_bytes = generate_annotated_pdf(
            entry["path"], spec, render_cfg, border=border, wrap=wrap,
            **build_marker_kwargs(half, frame_mm, frame_color, cross_mm),
        )
        doc = fitz.open("pdf", pdf_bytes)
        page = doc[0]
        scale = min(PREVIEW_MAX_PX / page.rect.width, PREVIEW_MAX_PX / page.rect.height, 1.0)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        doc.close()
        return Response(content=pix.tobytes("png"), media_type="image/png")

    @app.get("/api/generate")
    def generate(
        sid: str | None = Cookie(default=None),
        out_w: float = 100.0,
        out_h: float = 100.0,
        margin: float = 1.5,
        spacing: float = 50.0,
        marker: float = 1.0,
        border: bool = False,
        wrap: bool = False,
        half: bool = False,
        wrap_extra: float = 3.0,
        frame_mm: float = 1.0,
        frame_color: str = "gray",
        cross_mm: float = 1.2,
    ) -> Response:
        entry, spec, render_cfg = _common_params(
            sid, out_w, out_h, margin, spacing, marker, border, wrap, half, wrap_extra
        )
        pdf_bytes = generate_annotated_pdf(
            entry["path"], spec, render_cfg, border=border, wrap=wrap,
            **build_marker_kwargs(half, frame_mm, frame_color, cross_mm),
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=banner_oczka.pdf"},
        )

    return app


store = SessionStore()
app = create_app(store)
