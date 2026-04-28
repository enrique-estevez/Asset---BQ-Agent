"""CLI entry point — loads config from environment variables or .env file."""
import os
import asyncio
import logging
import uuid

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import google.auth
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agent import build_agent

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(
            f"Variable de entorno requerida no encontrada: '{name}'.\n"
            "Copia .env.example a .env y rellena los valores."
        )
    return value


def _load_config() -> dict:
    return {
        "project_id": _require("GCP_PROJECT_ID"),
        "dataset_id":  _require("BQ_DATASET_ID"),
        "location":    os.getenv("GCP_LOCATION", "europe-southwest1"),
        "model":       os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "app_name":    os.getenv("APP_NAME", "bq_agent"),
    }


def _apply_env(cfg: dict) -> None:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    os.environ["GOOGLE_CLOUD_PROJECT"]      = cfg["project_id"]
    os.environ["GOOGLE_CLOUD_LOCATION"]     = cfg["location"]


async def chat(cfg: dict) -> None:
    credentials, _ = google.auth.default()
    agent = build_agent(
        project_id=cfg["project_id"],
        dataset_id=cfg["dataset_id"],
        model=cfg["model"],
        credentials=credentials,
    )

    session_service = InMemorySessionService()
    user_id    = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    runner = Runner(agent=agent, app_name=cfg["app_name"], session_service=session_service)

    await session_service.create_session(
        app_name=cfg["app_name"], user_id=user_id, session_id=session_id
    )

    print("\n¡Hola! Soy tu agente de BigQuery.")
    print(f"  Proyecto : {cfg['project_id']}")
    print(f"  Dataset  : {cfg['dataset_id']}")
    print(f"  Modelo   : {cfg['model']}")
    print("\nEscribe tu pregunta en español. Escribe 'salir' para terminar.\n")

    while True:
        try:
            user_query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSesión finalizada.")
            break

        if not user_query:
            continue
        if user_query.lower() in ("salir", "exit", "quit"):
            print("¡Hasta pronto!")
            break

        content = types.Content(role="user", parts=[types.Part(text=user_query)])
        try:
            events = runner.run(user_id=user_id, session_id=session_id, new_message=content)
            answer = ""
            for event in events:
                if event.is_final_response() and event.content:
                    answer = event.content.parts[0].text.strip()
                    break
        except Exception as e:
            log.error("Error al procesar la consulta: %s", e)
            print("[Error] No se pudo procesar tu pregunta. Inténtalo de nuevo.\n")
            continue

        print(f"\n{answer if answer else '[Sin respuesta]'}\n")


def main() -> None:
    try:
        cfg = _load_config()
    except EnvironmentError as e:
        print(f"\n[Error de configuración]\n{e}\n")
        return

    _apply_env(cfg)
    asyncio.run(chat(cfg))


if __name__ == "__main__":
    main()
