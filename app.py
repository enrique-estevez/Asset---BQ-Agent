"""Streamlit UI — setup de conectores + chat conversacional con BigQuery."""
import os
import json
import uuid
import asyncio

import streamlit as st
import google.auth
from google.oauth2 import service_account
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agent import build_agent, AVAILABLE_MODELS, DEFAULT_MODEL, DEFAULT_LOCATION

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BQ Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS mínimo ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stChatMessage { border-radius: 10px; }
    div[data-testid="stSidebarContent"] { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


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
        st.markdown("## 🤖 BQ Agent")
        st.markdown(
            "Conecta tu entorno de Google Cloud para consultar tus datos "
            "en lenguaje natural."
        )
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
    st.markdown("## 🤖 BQ Agent")
    st.caption(
        f"Dataset `{cfg['dataset_id']}` · Proyecto `{cfg['project_id']}` · "
        f"Modelo `{cfg['model']}`"
    )

    # Historial de mensajes
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
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

            st.markdown(answer)
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
