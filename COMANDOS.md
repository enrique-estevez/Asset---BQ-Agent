# 📋 Comandos útiles — BQ Agent

Referencia rápida de todos los comandos para configurar, lanzar y gestionar el agente.
Pensado para **Windows + PowerShell**. Ejecuta los comandos desde la carpeta del proyecto.

> Sustituye los valores entre `<...>` por los tuyos:
> - `<TU_PROJECT_ID>` — ID de tu proyecto GCP (guion medio, p. ej. `mi-proyecto-123`)
> - `<TU_DATASET>` — nombre del dataset de BigQuery
> - `<TU_TABLA>` — nombre de la tabla
> - `<CARPETA_PROYECTO>` — ruta local donde clonaste el repo

> 💡 **Idea clave:** para *lanzar el front* solo necesitas el entorno virtual (`.venv`).
> Las credenciales de Google ya están guardadas en disco (paso 5) y la app las lee sola;
> **no** hace falta tener `gcloud` en el PATH para arrancar la web.

---

## 1. Las 3 piezas del sistema

| Pieza | ¿Acción cada vez? | Por qué |
|-------|:-----------------:|---------|
| Entorno Python (`.venv`) | ✅ Sí | Contiene Streamlit y las librerías |
| Credenciales (ADC) | ❌ No | Guardadas en `%APPDATA%\gcloud\` tras el login |
| Cliente / branding (`CLIENT_ID`) | Opcional | Elige la marca (default, acme, globex…) |

---

## 2. Lanzar el front (lo más habitual)

### Forma 1 — Activando el entorno virtual (recomendada)

```powershell
# 1. Ir a la carpeta del proyecto
cd "<CARPETA_PROYECTO>"

# 2. Activar el venv  (verás "(.venv)" al inicio del prompt)
.\.venv\Scripts\Activate.ps1

# 3. Lanzar el front
streamlit run app.py
```

- **Parar el servidor:** `Ctrl + C` en la terminal.
- **Salir del venv:** `deactivate`.

### Forma 2 — Sin activar, invocando el Python del venv

```powershell
cd "<CARPETA_PROYECTO>"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Mismo resultado; útil para un solo comando sin "entrar" al entorno.

### Forma 3 — CLI en vez de web

```powershell
.\.venv\Scripts\python.exe main.py
```

Chat por terminal (lee la configuración de `.env`). Escribe `salir` para terminar.

---

## 3. Elegir el cliente (branding)

Las marcas se definen en [branding/clientes.toml](branding/clientes.toml).

### Opción persistente — en `.env`
Edita el fichero `.env` y deja:
```
CLIENT_ID=acme
```
Arrancará siempre con esa marca.

### Opción puntual — variable de sesión (manda sobre `.env`)
```powershell
$env:CLIENT_ID = "acme"
streamlit run app.py
```

### Lanzar directamente con un cliente concreto (una sola línea)
```powershell
$env:CLIENT_ID="acme"; .\.venv\Scripts\python.exe -m streamlit run app.py
```

---

## 4. Personalizar o añadir un cliente (branding a medida)

El branding está **dirigido por configuración**: añadir una marca nueva no requiere tocar código.

### Paso 1 — Añadir el logo
Copia el logo (JPG, PNG o SVG) a la carpeta de logos:
```powershell
Copy-Item "C:\ruta\a\mi_logo.png" "branding\logos\micliente.png"
```

### Paso 2 — Añadir la marca en el TOML
Edita [branding/clientes.toml](branding/clientes.toml) y añade una sección nueva.
Los campos que falten heredan de `[default]`:

```toml
[micliente]
app_title    = "Mi Cliente · BQ Agent"      # título de la app y de la pestaña
page_icon    = "🟢"                          # emoji o ruta a imagen (favicon)
logo_path    = "branding/logos/micliente.png" # ruta relativa a la raíz del proyecto
tagline      = "Texto bajo el título en la pantalla de inicio."
primary      = "#00A86B"                      # color principal (botones, acentos)
bg           = "#FFFFFF"                       # color de fondo
secondary_bg = "#E8F5EE"                       # fondo del sidebar / secundarios
text         = "#1A1A1A"                       # color del texto
font         = "'Segoe UI', sans-serif"        # familia tipográfica CSS
```

### Paso 3 — Comprobar que la marca carga bien
```powershell
.\.venv\Scripts\python.exe -c "from branding import load_branding; print(load_branding('micliente'))"
```

### Paso 4 — Lanzar con tu cliente
```powershell
$env:CLIENT_ID="micliente"; .\.venv\Scripts\python.exe -m streamlit run app.py
```

> El tamaño del logo grande de la pantalla de inicio se controla en [app.py](app.py)
> con `render_logo(st, BRAND, width=320)` — sube o baja el `width` a gusto.

---

## 5. Parar / comprobar el front

### ¿Hay algo corriendo en el puerto 8501?
```powershell
Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue
```
Si no devuelve nada → no hay ningún Streamlit escuchando ahí.

### Parar el front
- **Si lo lanzaste en una terminal visible:** `Ctrl + C` en esa terminal.
- **Si no tienes la terminal a la vista** (lo cerraste, corre en segundo plano…):
  ```powershell
  Get-NetTCPConnection -LocalPort 8501 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
  ```

### Ver todos los procesos de Streamlit (por si usaste otro puerto)
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*streamlit*' } |
  Select-Object ProcessId, CommandLine
```
Y lo detienes con:
```powershell
Stop-Process -Id <PID> -Force
```

---

## 6. Configuración inicial (solo la primera vez)

### Entorno virtual y dependencias
```powershell
# Crear el entorno virtual
python -m venv .venv

# Instalar dependencias dentro del venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Autenticación con Google Cloud (ADC)
```powershell
gcloud auth login                                   # identidad para la CLI
gcloud auth application-default login               # credenciales para las librerías (ADC)
gcloud config set project <TU_PROJECT_ID>           # proyecto activo
gcloud auth application-default set-quota-project <TU_PROJECT_ID>
```

> Estas credenciales quedan guardadas en disco; no hay que repetirlas en cada arranque.

### Habilitar APIs (una vez por proyecto)
```powershell
gcloud services enable bigquery.googleapis.com aiplatform.googleapis.com --project=<TU_PROJECT_ID>
```

---

## 7. Datos en BigQuery

### Crear el dataset
```powershell
bq --location=europe-southwest1 mk -d <TU_PROJECT_ID>:<TU_DATASET>
```

### Cargar un CSV como tabla (esquema explícito de ejemplo)
```powershell
bq --location=europe-southwest1 load `
  --source_format=CSV --skip_leading_rows=1 `
  <TU_PROJECT_ID>:<TU_DATASET>.<TU_TABLA> `
  "data/mi_fichero.csv" `
  "Columna1:STRING,Columna2:FLOAT64,Columna3:FLOAT64"
```

### Comprobar la tabla
```powershell
bq query --use_legacy_sql=false --location=europe-southwest1 `
  "SELECT COUNT(*) AS filas FROM ``<TU_PROJECT_ID>.<TU_DATASET>.<TU_TABLA>``"
```

---

## 8. gcloud en el PATH (solo para comandos gcloud / bq)

Si abres una terminal nueva y `gcloud` no se reconoce, añádelo **para esa sesión**
(ruta estándar de instalación del SDK en Windows):
```powershell
$env:Path = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin;" + $env:Path
```
Comprobar que funciona:
```powershell
gcloud --version
```

> Recuerda: esto **solo** hace falta para `gcloud`/`bq`, no para lanzar el front.

---

## 9. Problemas típicos (Windows)

### `Activate.ps1` bloqueado por la política de ejecución
Permite scripts en tu usuario (una sola vez):
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
O usa la **Forma 2** (no requiere activar el venv).

### El puerto 8501 está ocupado
Streamlit usará el 8502 automáticamente, o dará error. Libera el 8501 con el comando del
apartado 5, o lanza en otro puerto:
```powershell
streamlit run app.py --server.port 8502
```

### El arranque tarda mucho (1-2 min)
El coste está en **importar las librerías** al arrancar (no en cada consulta). Suele deberse a
**poca RAM libre** (la app pesa varios cientos de MB y, si el sistema pagina a disco, el arranque
se dispara). Cierra apps que consuman memoria (navegador, Teams…) antes de lanzar, y **deja el
servidor abierto** en vez de reiniciarlo: una vez arrancado, las consultas del chat van rápidas.

### Comprobar configuración / cuenta activa de gcloud
```powershell
gcloud auth list      # cuentas autenticadas
gcloud config list    # proyecto y cuenta activos
```

---

## Resumen mínimo para recordar

```powershell
cd "<CARPETA_PROYECTO>"
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

- **Cliente:** en `.env` (`CLIENT_ID=...`)
- **Personalizar marca:** editar [branding/clientes.toml](branding/clientes.toml) + logo en `branding/logos/`
- **Parar:** `Ctrl + C`
- **Comprobar puerto:** `Get-NetTCPConnection -LocalPort 8501 -State Listen`
