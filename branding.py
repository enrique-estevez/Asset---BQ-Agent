"""White-label branding: carga la marca del cliente activo y la aplica a Streamlit.

El cliente activo se selecciona con la variable de entorno CLIENT_ID (default: "default").
Las marcas se definen en branding/clientes.toml — añadir un cliente no requiere tocar código.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

_BASE = Path(__file__).parent
_CONFIG = _BASE / "branding" / "clientes.toml"

# Valores de respaldo si falta el TOML o algún campo.
_FALLBACK = {
    "app_title":    "BQ Agent",
    "page_icon":    "🤖",
    "logo_path":    "",
    "tagline":      "Conecta tu entorno de Google Cloud para consultar tus datos en lenguaje natural.",
    "primary":      "#FF4B4B",
    "bg":           "#FFFFFF",
    "secondary_bg": "#F0F2F6",
    "text":         "#262730",
    "font":         "sans-serif",
}


def load_branding(client_id: str | None = None) -> dict:
    """Resuelve la marca del cliente activo (env CLIENT_ID si no se pasa explícito).

    Orden de precedencia: sección del cliente > sección [default] del TOML > _FALLBACK.
    """
    client_id = client_id or os.getenv("CLIENT_ID", "default")
    cfg = dict(_FALLBACK)

    if _CONFIG.exists():
        with open(_CONFIG, "rb") as f:
            data = tomllib.load(f)
        for section in ("default", client_id):
            values = data.get(section)
            if values:
                cfg.update({k: v for k, v in values.items() if v is not None})

    cfg["client_id"] = client_id
    return cfg


def _brand_css(cfg: dict) -> str:
    return f"""
<style>
    .block-container {{ padding-top: 2rem; }}
    .stChatMessage {{ border-radius: 10px; }}
    div[data-testid="stSidebarContent"] {{ padding-top: 1.5rem; }}

    .stApp {{ background-color: {cfg['bg']}; color: {cfg['text']}; }}
    html, body, [class*="st-"] {{ font-family: {cfg['font']}; }}
    section[data-testid="stSidebar"] {{ background-color: {cfg['secondary_bg']}; }}

    /* Botón primario con el color de marca */
    button[kind="primary"],
    button[data-testid="stBaseButton-primary"] {{
        background-color: {cfg['primary']};
        border-color: {cfg['primary']};
    }}
</style>
"""


def apply_branding(st, cfg: dict) -> None:
    """Aplica logo de sidebar + CSS de marca. Debe llamarse tras st.set_page_config()."""
    logo = cfg.get("logo_path")
    if logo:
        logo_file = _BASE / logo
        if logo_file.exists():
            st.logo(str(logo_file))

    st.markdown(_brand_css(cfg), unsafe_allow_html=True)


def render_logo(st, cfg: dict, width: int = 320) -> None:
    """Renderiza el logo en grande dentro del cuerpo de la página (no en el sidebar).

    Soporta imágenes raster (JPG/PNG) y SVG. Si no hay logo o no existe, no hace nada.
    """
    logo = cfg.get("logo_path")
    if not logo:
        return
    logo_file = _BASE / logo
    if not logo_file.exists():
        return

    if logo_file.suffix.lower() == ".svg":
        svg = logo_file.read_text(encoding="utf-8")
        st.markdown(
            f'<div style="width:{width}px;max-width:100%;margin:0 0 1rem 0">{svg}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.image(str(logo_file), width=width)
