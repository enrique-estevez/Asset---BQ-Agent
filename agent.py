from __future__ import annotations

import google.auth
from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
]

DEFAULT_MODEL    = "gemini-2.5-flash"
DEFAULT_LOCATION = "europe-southwest1"


def build_agent(
    project_id: str,
    dataset_id: str,
    model: str = DEFAULT_MODEL,
    credentials=None,
) -> Agent:
    """Build a BigQuery ADK agent for a given GCP project and dataset.

    Credentials can be any google.auth.credentials.Credentials object.
    If omitted, Application Default Credentials are used.
    Write operations are always blocked.
    """
    if credentials is None:
        credentials, _ = google.auth.default()

    tool_config = BigQueryToolConfig(
        project_id=project_id,
        dataset_id=dataset_id,
        credentials=credentials,
        write_mode=WriteMode.BLOCKED,
    )
    toolset = BigQueryToolset(
        credentials_config=BigQueryCredentialsConfig(credentials=credentials),
        bigquery_tool_config=tool_config,
    )

    return Agent(
        model=model,
        name="agente_bigquery",
        description="Agente conversacional que responde preguntas sobre datos en BigQuery.",
        instruction=(
            "Eres un experto analista de datos. Tu objetivo es responder a las preguntas del usuario "
            f"consultando las tablas del conjunto de datos '{dataset_id}' en el proyecto '{project_id}'. "
            "Habla siempre en español. Explora las tablas disponibles, revisa sus esquemas "
            "y combínalas con JOINs si es necesario para dar la respuesta más completa y precisa. "
            "Cuando devuelvas datos tabulares, formátalos como tabla Markdown."
        ),
        tools=[toolset],
    )
