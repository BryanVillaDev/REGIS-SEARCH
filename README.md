# REGIS Search

App Dockerizada con FastAPI, React y ClickHouse para consultar registros ANI, contactos y busquedas masivas por cedula.

## Que incluye

- Login con JWT y usuarios guardados en ClickHouse.
- Auditoria de busquedas en `app.regis_search_audit`.
- Consulta por `ANINuip` con ubicaciones resueltas y contactos.
- Busqueda por nombres/apellidos con paginacion.
- Busqueda masiva por cedulas mediante jobs procesados por un worker.
- Busqueda masiva por nombres con ranking de la coincidencia mas cercana (tolerante a typos, tildes y al orden de los tokens). Acepta entradas en 1, 2 o 4 columnas.
- Descarga de resultados en CSV y XLSX cuando el lote cabe dentro del limite configurado.

## Inicio rapido

1. Copia `.env.example` a `.env`.
2. Configura `CLICKHOUSE_URL`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD` y `JWT_SECRET`.
3. Define `REGIS_BOOTSTRAP_ADMIN_PASSWORD` con una clave fuerte.
4. Levanta el stack:

```powershell
docker compose up --build
```

5. Abre `http://localhost:5173` e inicia sesion con el usuario bootstrap.

## Entorno local con ClickHouse propio

El `docker-compose.yml` de la raiz es el de produccion (Dokploy) y se conecta a un ClickHouse
externo. Para correr **todo en local** (incluyendo ClickHouse) y traer la data real del cloud,
usa `docker-compose.local.yml`, que es autocontenido y persiste la data en el volumen
`clickhouse_data`.

```powershell
# 1. Config
cp .env.local.example .env.local      # secretos del stack local
cp .env.cloud.example .env.cloud      # credenciales reales del ClickHouse cloud (origen)

# 2. Levantar stack (ClickHouse + api + worker + frontend)
docker compose -f docker-compose.local.yml --env-file .env.local up -d --build

# 3. (paso 0) Ver el tamano REAL en disco antes de descargar nada
./scripts/sync-clickhouse.ps1 -MeasureOnly

# 4. Sincronizar la data del cloud -> local (persiste en el volumen)
./scripts/sync-clickhouse.ps1
#   - solo una tabla:    ./scripts/sync-clickhouse.ps1 -Tables ani_fin
#   - forzar refresco:   ./scripts/sync-clickhouse.ps1 -Force
```

- App de busquedas: `http://localhost:8080` (login con el admin bootstrap).
- API: `http://localhost:8080/api/health` (el frontend la proxya; no hay puerto 8000).
- ClickHouse local: `localhost:8123` (HTTP) / `localhost:9000` (nativo).

La data queda en el volumen `clickhouse_data`. En arranques siguientes
(`docker compose -f docker-compose.local.yml --env-file .env.local up -d`) **no** se re-descarga:
la info sigue sincronizada. Solo vuelve a sincronizar si corres el script otra vez (o con `-Force`).

El script `scripts/sync-clickhouse.ps1` corre **desde el host por HTTP** (no usa el protocolo
nativo 9000 ni el contenedor): autodescubre las tablas `MergeTree` de las bases en
`CLOUD_CH_DATABASES`, recrea su esquema exacto y copia la data en formato `Native` con gzip
en el cable. Esto funciona aun cuando el contenedor de Docker no logra salir al cloud por el
puerto nativo (un problema comun de Docker Desktop en Windows/Wi-Fi).

## Seguridad

La clave de ClickHouse no esta hardcodeada. Como las credenciales originales fueron compartidas en chat, rota la contrasena antes de usar esta app en produccion. Los archivos `.env.local` y `.env.cloud` estan en `.gitignore`; nunca commitees credenciales reales.

## Servicios

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- Healthcheck: `http://localhost:8000/api/health`

## Comandos utiles

```powershell
docker compose logs -f api
docker compose logs -f worker
docker compose exec api pytest
```

## Notas de ClickHouse

Al iniciar, la API crea estas tablas si no existen:

- `app.regis_users`
- `app.regis_search_audit`
- `app.regis_search_jobs`
- `app.regis_search_job_inputs`
- `app.regis_search_job_name_inputs`

El worker esta pensado como instancia unica para el MVP.
