"""Streamlit UI — setup de conectores + chat conversacional con BigQuery."""
import os
import re
import json
import uuid
import asyncio

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import google.auth
from google.oauth2 import service_account
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agent import build_agent, AVAILABLE_MODELS, DEFAULT_MODEL, DEFAULT_LOCATION
from branding import load_branding, apply_branding, render_logo

# ── Branding (white-label por cliente vía CLIENT_ID) ─────────────────────────────
BRAND = load_branding()

st.set_page_config(
    page_title=BRAND["app_title"],
    page_icon=BRAND["page_icon"],
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_branding(st, BRAND)


# ── Helpers de sesión ADK ──────────────────────────────────────────────────────

def _init_runner(agent, app_name: str, user_id: str, session_id: str) -> Runner:
    session_service = InMemorySessionService()
    asyncio.run(
        session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
    )
    return Runner(agent=agent, app_name=app_name, session_service=session_service)


def _run_query(query: str) -> str:
    content = types.Content(role="user", parts=[types.Part(text=query)])
    events = st.session_state.runner.run(
        user_id=st.session_state.user_id,
        session_id=st.session_state.session_id,
        new_message=content,
    )
    for event in events:
        if event.is_final_response() and event.content:
            return event.content.parts[0].text.strip()
    return ""


# ── Renderizado de respuestas (texto + gráficos) ────────────────────────────────

_CHART_BLOCK_RE = re.compile(r"```chart\s*(.*?)```", re.DOTALL)


def _render_chart(spec: dict) -> None:
    data = spec.get("data")
    if not data:
        return
    df = pd.DataFrame(data)
    if df.empty:
        return

    title = spec.get("title")
    if title:
        st.caption(title)

    x = spec.get("x")
    if x and x in df.columns:
        df = df.set_index(x)

    y = spec.get("y")
    if y:
        cols = [c for c in y if c in df.columns]
        if cols:
            df = df[cols]

    chart_type = (spec.get("type") or "bar").lower()
    if chart_type == "line":
        st.line_chart(df)
    elif chart_type == "area":
        st.area_chart(df)
    else:
        st.bar_chart(df)


def _render_assistant(content: str) -> None:
    """Render an assistant message, turning ```chart JSON blocks into charts."""
    cursor = 0
    for match in _CHART_BLOCK_RE.finditer(content):
        text_before = content[cursor:match.start()].strip()
        if text_before:
            st.markdown(text_before)
        raw = match.group(1).strip()
        try:
            _render_chart(json.loads(raw))
        except (json.JSONDecodeError, ValueError, KeyError):
            st.markdown(f"```\n{raw}\n```")
        cursor = match.end()

    rest = content[cursor:].strip()
    if rest:
        st.markdown(rest)


# ── Estado de sesión ───────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "configured": False,
        "messages":   [],
        "runner":     None,
        "user_id":    str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "config":     {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset() -> None:
    st.session_state.configured = False
    st.session_state.messages   = []
    st.session_state.runner     = None
    st.session_state.user_id    = str(uuid.uuid4())
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.config     = {}


# ── Pantalla de configuración ──────────────────────────────────────────────────

def _show_setup() -> None:
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        render_logo(st, BRAND, width=320)
        st.markdown(f"## {BRAND['page_icon']} {BRAND['app_title']}")
        st.markdown(BRAND["tagline"])
        st.divider()

        with st.form("setup_form", clear_on_submit=False):

            # ── Proyecto y Dataset ─────────────────────────────────────────────
            st.markdown("#### Google Cloud")
            c1, c2 = st.columns(2)
            with c1:
                project_id = st.text_input(
                    "Project ID *",
                    placeholder="mi-proyecto-gcp",
                    help="ID del proyecto GCP donde está tu BigQuery.",
                )
            with c2:
                dataset_id = st.text_input(
                    "BigQuery Dataset ID *",
                    placeholder="mi_dataset",
                    help="Nombre del dataset de BigQuery a consultar.",
                )

            c3, c4 = st.columns(2)
            with c3:
                location = st.text_input(
                    "Región",
                    value=DEFAULT_LOCATION,
                    help="Región de tus recursos GCP.",
                )
            with c4:
                model = st.selectbox(
                    "Modelo Gemini",
                    options=AVAILABLE_MODELS,
                    index=AVAILABLE_MODELS.index(DEFAULT_MODEL),
                    help="Modelo Gemini que procesará las consultas.",
                )

            st.divider()

            # ── Credenciales ───────────────────────────────────────────────────
            st.markdown("#### Credenciales GCP")
            creds_mode = st.radio(
                "Fuente de credenciales",
                options=[
                    "Application Default Credentials (ADC)",
                    "Fichero de cuenta de servicio (JSON)",
                ],
                help=(
                    "**ADC**: usa las credenciales del entorno "
                    "(`gcloud auth application-default login`, Workload Identity, etc.).\n\n"
                    "**JSON**: sube el fichero de la cuenta de servicio. "
                    "No se guarda en disco."
                ),
            )

            uploaded = None
            if "JSON" in creds_mode:
                uploaded = st.file_uploader(
                    "Fichero JSON de cuenta de servicio",
                    type=["json"],
                    help="El fichero se usa en memoria y nunca se escribe en disco.",
                )

            st.divider()
            submitted = st.form_submit_button(
                "Conectar →", type="primary", use_container_width=True
            )

        if submitted:
            _handle_connect(project_id, dataset_id, location, model, creds_mode, uploaded)


def _handle_connect(project_id, dataset_id, location, model, creds_mode, uploaded) -> None:
    errors = []
    if not project_id:
        errors.append("Project ID es obligatorio.")
    if not dataset_id:
        errors.append("Dataset ID es obligatorio.")
    if "JSON" in creds_mode and not uploaded:
        errors.append("Debes subir el fichero JSON de la cuenta de servicio.")

    if errors:
        for err in errors:
            st.error(err)
        return

    with st.spinner("Inicializando agente…"):
        try:
            # Credenciales
            if "JSON" in creds_mode:
                creds_data = json.load(uploaded)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_data,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
            else:
                credentials, _ = google.auth.default()

            # Variables de entorno requeridas por el SDK de Vertex AI
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
            os.environ["GOOGLE_CLOUD_PROJECT"]      = project_id
            os.environ["GOOGLE_CLOUD_LOCATION"]     = location

            # Construir agente y runner
            agent = build_agent(
                project_id=project_id,
                dataset_id=dataset_id,
                model=model,
                credentials=credentials,
            )
            runner = _init_runner(
                agent,
                app_name="bq_agent",
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
            )

            st.session_state.runner     = runner
            st.session_state.configured = True
            st.session_state.config     = {
                "project_id": project_id,
                "dataset_id": dataset_id,
                "location":   location,
                "model":      model,
            }
            st.rerun()

        except Exception as e:
            st.error(f"Error al conectar con GCP: {e}")


# ── Pantalla de chat ───────────────────────────────────────────────────────────

def _show_chat() -> None:
    cfg = st.session_state.config

    # Sidebar con config activa
    with st.sidebar:
        st.markdown("### Conexión activa")
        st.markdown(f"**Proyecto:** `{cfg['project_id']}`")
        st.markdown(f"**Dataset:** `{cfg['dataset_id']}`")
        st.markdown(f"**Región:** `{cfg['location']}`")
        st.markdown(f"**Modelo:** `{cfg['model']}`")
        st.divider()
        st.markdown("**Historial**")
        st.caption(f"{len(st.session_state.messages) // 2} consultas realizadas")
        st.divider()
        if st.button("Reconfigurar", use_container_width=True):
            _reset()
            st.rerun()
        if st.button("Limpiar conversación", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Cabecera
    st.markdown(f"## {BRAND['page_icon']} {BRAND['app_title']}")
    st.caption(
        f"Dataset `{cfg['dataset_id']}` · Proyecto `{cfg['project_id']}` · "
        f"Modelo `{cfg['model']}`"
    )

    # Historial de mensajes
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                _render_assistant(msg["content"])
            else:
                st.markdown(msg["content"])

    # Input del usuario
    if prompt := st.chat_input("¿Qué te gustaría saber de tus datos?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando BigQuery…"):
                try:
                    answer = _run_query(prompt)
                    if not answer:
                        answer = (
                            "No obtuve una respuesta del agente. "
                            "Intenta reformular la pregunta."
                        )
                except Exception as e:
                    answer = f"Error al procesar la consulta: {e}"

            _render_assistant(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    _init_state()
    if not st.session_state.configured:
        _show_setup()
    else:
        _show_chat()


if __name__ == "__main__":
    main()
