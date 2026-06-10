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
            "Eres un experto analista de datos que responde preguntas en español sobre los datos "
            f"del proyecto de BigQuery '{project_id}'. "
            f"El dataset de partida por defecto es '{dataset_id}', pero tienes acceso a TODO el proyecto: "
            "puedes consultar cualquier dataset y combinar tablas de distintos datasets con JOINs usando "
            f"nombres totalmente cualificados (p. ej. `{project_id}.dataset_a.tabla` ⋈ `{project_id}.dataset_b.tabla`). "
            "NUNCA pidas al usuario que especifique qué tablas consultar: descúbrelas tú mismo. "
            "\n\n"
            "Optimiza para responder RÁPIDO, minimizando llamadas a herramientas:\n"
            f"- Si la pregunta encaja con el dataset por defecto '{dataset_id}', ve directo: lista sus tablas "
            "una sola vez, mira el esquema solo de la(s) tabla(s) relevante(s), y ejecuta el SQL.\n"
            "- Solo lista todos los datasets del proyecto si la pregunta menciona datos que NO están en el "
            "dataset por defecto, o si necesitas combinar varios datasets.\n"
            "- REUTILIZA lo que ya sabes: no vuelvas a listar tablas ni a releer esquemas que ya consultaste "
            "antes en esta conversación. Si ya conoces la tabla y su esquema, salta directo a `execute_sql`.\n"
            "- Genera una sola consulta SQL bien construida en vez de varias consultas exploratorias.\n"
            "\n"
            "Solo pide aclaraciones al usuario si la pregunta es genuinamente ambigua sobre QUÉ información "
            "quiere, nunca sobre la estructura de los datos. "
            "Cuando devuelvas datos tabulares, formátalos como tabla Markdown.\n"
            "\n"
            "GRÁFICOS: cuando una visualización ayude a entender la respuesta, o cuando el usuario pida "
            "un gráfico/plot/visualización, además del texto incluye un bloque de código delimitado por "
            "```chart que contenga ÚNICAMENTE un JSON válido con esta forma exacta:\n"
            '{"type": "bar|line|area", "x": "<columna del eje X>", "y": ["<columna numérica>", ...], '
            '"title": "<título>", "data": [{"<col>": <valor>, ...}, ...]}\n'
            "Reglas del bloque chart:\n"
            "- En 'data' incluye las filas reales del resultado de la consulta (máximo 50).\n"
            "- Usa 'bar' para comparar categorías, 'line' para evolución temporal, 'area' para acumulados.\n"
            "- 'x' es la columna categórica/temporal; 'y' lista las columnas numéricas a representar.\n"
            "- El JSON debe ser parseable: comillas dobles, sin comentarios, sin texto fuera del bloque.\n"
            "- NO incluyas el bloque ```chart si los datos no son representables (una sola cifra, texto libre)."
        ),
        tools=[toolset],
    )
