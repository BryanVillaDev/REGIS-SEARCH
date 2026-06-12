<#
.SYNOPSIS
  Sincroniza la data del ClickHouse CLOUD al ClickHouse LOCAL (Docker) via remote().

.DESCRIPTION
  Desde el contenedor de ClickHouse local, usa la funcion remote() para:
    0) Medir el tamano REAL en disco de las tablas en el cloud (antes de descargar).
    1) Autodescubrir las tablas MergeTree de cada base en CLOUD_CH_DATABASES.
    2) Recrear el esquema EXACTO copiando el create_table_query del cloud.
    3) Copiar la data con INSERT ... SELECT * FROM remote(...) (streaming, ya comprimido).
    4) Verificar comparando count() local vs remoto.
  Es idempotente: si el conteo local ya coincide con el remoto, salta la tabla (salvo -Force).

.EXAMPLE
  ./scripts/sync-clickhouse.ps1 -MeasureOnly      # solo medir, no descargar
  ./scripts/sync-clickhouse.ps1                   # sincronizar todo
  ./scripts/sync-clickhouse.ps1 -Tables ani_fin   # solo una tabla
  ./scripts/sync-clickhouse.ps1 -Force            # re-descargar aunque ya este sincronizada
#>
[CmdletBinding()]
param(
  [string]$ComposeFile = "docker-compose.local.yml",
  [string]$CloudEnv    = ".env.cloud",
  [string]$LocalEnv    = ".env.local",
  [string[]]$Tables,        # opcional: limitar a estas tablas
  [switch]$MeasureOnly,     # solo medir tamano real, no copiar
  [switch]$Force            # re-copiar aunque el conteo coincida
)
$ErrorActionPreference = "Stop"

# --- cargar .env.cloud y .env.local en variables de entorno ---
foreach ($f in @($CloudEnv, $LocalEnv)) {
  if (-not (Test-Path $f)) { throw "No existe $f. Copia el .example correspondiente y rellena los valores." }
  Get-Content $f | Where-Object { $_ -match '=' -and $_ -notmatch '^\s*#' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    Set-Item "env:$($k.Trim())" $v.Trim()
  }
}

$H  = $env:CLOUD_CH_HOST
$P  = $env:CLOUD_CH_PORT
$U  = $env:CLOUD_CH_USER
$PW = $env:CLOUD_CH_PASSWORD
$DBs = ($env:CLOUD_CH_DATABASES -split ',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }

# remote('host:port','db.tabla','user','pass')  -- el backtick escapa los dos puntos
function Rmt($obj) { "remote('$H`:$P','$obj','$U','$PW')" }

# Ejecuta SQL en el ClickHouse LOCAL (via stdin del contenedor) y devuelve texto limpio.
function CH([string]$sql) {
  $out = $sql | docker compose -f $ComposeFile exec -T clickhouse `
    clickhouse-client --user default --password $env:CLICKHOUSE_PASSWORD --multiquery 2>&1
  if ($LASTEXITCODE -ne 0) { throw "clickhouse-client fallo:`n$out" }
  return ($out -join "`n").Trim()
}

# --- PASO 0: medir tamano real en el cloud ---
$dbList = ($DBs | ForEach-Object { "'$_'" }) -join ','
Write-Host "== Tamano real en el cloud (bytes_on_disk = lo que se descarga/almacena) ==" -ForegroundColor Cyan
CH @"
SELECT database, table, formatReadableSize(sum(bytes_on_disk)) AS disk, sum(rows) AS rows
FROM $(Rmt 'system.parts')
WHERE active AND database IN ($dbList)
GROUP BY database, table
ORDER BY sum(bytes_on_disk) DESC
"@
if ($MeasureOnly) { Write-Host "`n(-MeasureOnly) No se descargo nada." -ForegroundColor Yellow; return }

foreach ($db in $DBs) {
  CH "CREATE DATABASE IF NOT EXISTS $db" | Out-Null

  # autodescubrir tablas (pequenas primero, para wins rapidos)
  $names = (CH @"
SELECT name FROM $(Rmt 'system.tables')
WHERE database='$db' AND engine LIKE '%MergeTree%'
ORDER BY total_bytes
"@) -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }

  if ($Tables) { $names = $names | Where-Object { $Tables -contains $_ } }
  if (-not $names) { Write-Host "Sin tablas que sincronizar en '$db'." -ForegroundColor Yellow; continue }

  foreach ($t in $names) {
    Write-Host "`n== $db.$t ==" -ForegroundColor Cyan

    # 1) recrear esquema exacto desde el cloud (DDL raw, una sola fila)
    $ddl = CH "SELECT create_table_query FROM $(Rmt 'system.tables') WHERE database='$db' AND name='$t' FORMAT TabSeparatedRaw"
    $ddl = $ddl -replace '^CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS '
    CH $ddl | Out-Null

    # 2) conteos
    $rc = [int64](CH "SELECT count() FROM $(Rmt "$db.$t")")
    $lc = [int64](CH "SELECT count() FROM $db.$t")
    if (-not $Force -and $lc -eq $rc -and $rc -gt 0) {
      Write-Host "ya sincronizada ($lc filas) -> salto" -ForegroundColor Green
      continue
    }

    # 3) copiar (truncar para idempotencia)
    Write-Host "copiando $rc filas..." -ForegroundColor Gray
    CH "TRUNCATE TABLE $db.$t" | Out-Null
    CH "INSERT INTO $db.$t SELECT * FROM $(Rmt "$db.$t") SETTINGS max_execution_time=0, max_insert_threads=4, max_threads=4" | Out-Null

    # 4) verificar
    $lc2 = [int64](CH "SELECT count() FROM $db.$t")
    if ($lc2 -eq $rc) { Write-Host "remoto=$rc local=$lc2 -> OK" -ForegroundColor Green }
    else { Write-Host "remoto=$rc local=$lc2 -> DESAJUSTE" -ForegroundColor Red }
  }
}

Write-Host "`nSincronizacion terminada." -ForegroundColor Cyan
