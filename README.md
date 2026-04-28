# 🤖 BQ Agent

Agente conversacional en lenguaje natural para consultar datos en **Google BigQuery**, construido sobre [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) y **Gemini 2.5**.

Permite hacer preguntas en español sobre cualquier dataset de BigQuery sin escribir SQL. Disponible como interfaz web (Streamlit) o como CLI de terminal.

---

## Arquitectura

```
BQ agent/
├── agent.py          ← Núcleo del agente ADK (agnóstico a configuración)
├── app.py            ← Interfaz web Streamlit  →  streamlit run app.py
├── main.py           ← CLI de terminal          →  python main.py
├── run.bat           ← Arranque Windows (doble clic)
├── .env.example      ← Plantilla de variables de entorno
├── .gitignore
├── requirements.txt
├── docs/
│   └── Conversational Agent - BQ OpenAPI Integration.pdf
└── data/             (excluida de git)
    └── 2020-2025.csv
```

**Separación de responsabilidades:**
- `agent.py` — construye el agente ADK, no conoce ni la UI ni la configuración del entorno
- `app.py` — recoge la configuración del usuario en un formulario y gestiona el chat
- `main.py` — alternativa CLI que lee la configuración desde variables de entorno

El agente tiene acceso de **sólo lectura** a BigQuery (`WriteMode.BLOCKED`).

---

## Requisitos previos

- Python 3.10+
- Cuenta GCP con BigQuery habilitado y Vertex AI activado
- Credenciales GCP: cuenta de servicio JSON **o** Application Default Credentials

```bash
# Opción ADC (recomendado para desarrollo local)
gcloud auth application-default login
```

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd bq-agent

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias (7 paquetes)
pip install -r requirements.txt
```

---

## Configuración

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

| Variable | Descripción | Obligatoria |
|----------|-------------|:-----------:|
| `GCP_PROJECT_ID` | ID del proyecto GCP | ✅ |
| `BQ_DATASET_ID` | Nombre del dataset de BigQuery | ✅ |
| `GCP_LOCATION` | Región GCP — default: `europe-southwest1` | |
| `GEMINI_MODEL` | Modelo — default: `gemini-2.5-flash` | |
| `GOOGLE_APPLICATION_CREDENTIALS` | Ruta al JSON de cuenta de servicio | Solo si no usas ADC |

> **Seguridad:** el fichero `.env` y cualquier `*.json` de credenciales están excluidos del control de versiones por `.gitignore`. Nunca los commitees.

---

## Uso

### Interfaz web (recomendado)

```bash
# Windows: doble clic en run.bat
# o desde terminal:
python -m streamlit run app.py
```

Al abrirse el navegador en `http://localhost:8501`, el formulario de configuración solicitará:

- **Project ID** y **Dataset ID** de BigQuery
- **Credenciales GCP**: Application Default Credentials o fichero JSON subido en el momento (se usa en memoria, nunca se guarda en disco)

Una vez conectado, escribe tus preguntas en español:

> *¿Qué tablas hay disponibles en el dataset?*
> *Muestra las ventas totales por región del último trimestre*
> *¿Cuántos clientes únicos hay en la tabla de pedidos?*

El sidebar muestra la configuración activa y permite reconfigurar o limpiar la conversación sin reiniciar la app.

### CLI

```bash
python main.py
```

Requiere `.env` configurado. Útil para pruebas rápidas o integración en scripts.

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| Agente | Google ADK | 1.13.0 |
| Modelo | Gemini 2.5 Flash (Vertex AI) | — |
| Datos | Google BigQuery | ≥ 3.25.0 |
| Auth | google-auth | ≥ 2.30.0 |
| Interfaz web | Streamlit | ≥ 1.39.0 |
| Config | python-dotenv | ≥ 1.0.0 |

---

## Seguridad

- Escrituras en BigQuery **bloqueadas** por diseño (`WriteMode.BLOCKED`)
- Credenciales JSON procesadas en memoria, nunca escritas en disco
- `.gitignore` excluye `*.json`, `.env`, `*.csv` y `docs/*.pdf`
- Sin valores hardcodeados en el código — toda la configuración es externa

---

## Roadmap

- [ ] Validación de conectividad en el formulario de setup (query `SELECT 1` al conectar)
- [ ] Persistencia de historial de conversación entre recargas
- [ ] Selector dinámico de dataset/tabla desde la API de BigQuery
- [ ] Activar `BuiltInPlanner` con thinking budget configurable
- [ ] Tests unitarios con mock del BigQuery toolset
- [ ] CI/CD con GitHub Actions
