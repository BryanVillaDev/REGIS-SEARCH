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

## Seguridad

La clave de ClickHouse no esta hardcodeada. Como las credenciales originales fueron compartidas en chat, rota la contrasena antes de usar esta app en produccion.

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
