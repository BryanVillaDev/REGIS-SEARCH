<#
.SYNOPSIS
  Sincroniza la data del ClickHouse CLOUD al ClickHouse LOCAL por HTTP, corriendo
  desde el HOST con curl.

.DESCRIPTION
  No usa el protocolo nativo (9000) ni `docker compose exec`: habla HTTP directo
  desde tu Windows (que SI alcanza el cloud) hacia:
    - CLOUD:  http://CLOUD_CH_HOST:CLOUD_CH_HTTP_PORT  (si hay Traefik/Dokploy: dominio + puerto 80)
    - LOCAL:  http://localhost:8123  (puerto publicado por docker-compose.local.yml)

  Por cada tabla MergeTree de las bases en CLOUD_CH_DATABASES:
    0) Mide el tamano REAL en disco en el cloud (-MeasureOnly).
    1) Copia el esquema exacto (create_table_query del cloud).
    2) Copia la data EN TROZOS (formato Native, gzip en el cable) para no agotar la
       memoria del ClickHouse local:
         - llave de orden numerica de una columna -> trozos por RANGO (usa el indice).
         - llave compuesta / no numerica          -> trozos por HASH (cityHash64 % K).
       Tablas chicas (<= RowsPerChunk) van de una sola.
    3) Verifica comparando count() local vs cloud. Idempotente (salta si ya coincide).

.EXAMPLE
  ./scripts/sync-clickhouse.ps1 -MeasureOnly        # solo medir
  ./scripts/sync-clickhouse.ps1                     # sincronizar todo (por trozos)
  ./scripts/sync-clickhouse.ps1 -Tables ani_fin     # solo una tabla
  ./scripts/sync-clickhouse.ps1 -Force              # re-descargar aunque ya este
  ./scripts/sync-clickhouse.ps1 -RowsPerChunk 1000000   # trozos mas chicos (menos RAM)
  ./scripts/sync-clickhouse.ps1 -NoCompress         # sin gzip (si gzip da problemas)
#>
[CmdletBinding()]
param(
  [string]$CloudEnv = ".env.cloud",
  [string]$LocalEnv = ".env.local",
  [string]$LocalUrl = "http://localhost:8123",
  [string[]]$Tables,            # opcional: limitar a estas tablas
  [int64]$RowsPerChunk = 3000000,  # filas por trozo (baja este numero si hay OOM)
  [switch]$MeasureOnly,         # solo medir tamano real
  [switch]$Force,               # re-copiar aunque el conteo coincida
  [switch]$NoCompress,          # desactivar gzip en el cable
  [string]$TempDir = $env:TEMP
)
$ErrorActionPreference = "Stop"

# --- cargar .env.cloud y .env.local ---
foreach ($f in @($CloudEnv, $LocalEnv)) {
  if (-not (Test-Path $f)) { throw "No existe $f. Copia el .example correspondiente y rellena los valores." }
  Get-Content $f | Where-Object { $_ -match '=' -and $_ -notmatch '^\s*#' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    Set-Item "env:$($k.Trim())" $v.Trim()
  }
}

$H   = $env:CLOUD_CH_HOST
$HP  = if ($env:CLOUD_CH_HTTP_PORT) { $env:CLOUD_CH_HTTP_PORT } else { "8123" }
$U   = $env:CLOUD_CH_USER
$PW  = $env:CLOUD_CH_PASSWORD
$LU  = if ($env:CLICKHOUSE_USER) { $env:CLICKHOUSE_USER } else { "default" }
$LPW = $env:CLICKHOUSE_PASSWORD
$CloudUrl = "http://${H}:${HP}"
$DBs = ($env:CLOUD_CH_DATABASES -split ',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }

$curl = "$env:SystemRoot\System32\curl.exe"
if (-not (Test-Path $curl)) { $curl = "curl.exe" }

# Consulta corta al CLOUD (texto). El body es el SQL.
function Cloud([string]$sql) {
  $r = & $curl -sS --fail-with-body -u "${U}:${PW}" "$CloudUrl/?max_execution_time=0" --data-binary $sql 2>&1
  if ($LASTEXITCODE -ne 0) { throw "CLOUD query fallo:`n$($r | Out-String)" }
  return (($r | Out-String).Trim())
}
# Consulta corta al LOCAL (texto).
function Local([string]$sql) {
  $r = & $curl -sS --fail-with-body -u "${LU}:${LPW}" "$LocalUrl/" --data-binary $sql 2>&1
  if ($LASTEXITCODE -ne 0) { throw "LOCAL query fallo:`n$($r | Out-String)" }
  return (($r | Out-String).Trim())
}
# Exporta del cloud (con WHERE) a $tmp e inserta en el local. Tunea memoria del insert.
function Copy-Chunk([string]$db, [string]$t, [string]$where, [string]$tmp) {
  $sel  = "SELECT * FROM $db.$t $where FORMAT Native"
  $insQ = ("INSERT INTO $db.$t FORMAT Native") -replace ' ', '+'
  $insOpts = "max_insert_threads=1&max_threads=2"
  if ($NoCompress) {
    & $curl --fail-with-body -# -u "${U}:${PW}" "$CloudUrl/?max_execution_time=0" --data-binary $sel -o $tmp
    if ($LASTEXITCODE -ne 0) { throw "export fallo ($db.$t): $where" }
    & $curl --fail-with-body -# -u "${LU}:${LPW}" "$LocalUrl/?query=$insQ&$insOpts" --data-binary "@$tmp"
    if ($LASTEXITCODE -ne 0) { throw "import fallo ($db.$t): $where" }
  } else {
    & $curl --fail-with-body -# -u "${U}:${PW}" -H "Accept-Encoding: gzip" `
      "$CloudUrl/?enable_http_compression=1&max_execution_time=0" --data-binary $sel -o $tmp
    if ($LASTEXITCODE -ne 0) { throw "export fallo ($db.$t): $where" }
    & $curl --fail-with-body -# -u "${LU}:${LPW}" -H "Content-Encoding: gzip" `
      "$LocalUrl/?enable_http_compression=1&query=$insQ&$insOpts" --data-binary "@$tmp"
    if ($LASTEXITCODE -ne 0) { throw "import fallo ($db.$t): $where" }
  }
}

# --- preflight ---
Write-Host "Probando cloud ($CloudUrl) ..." -NoNewline
[void](Cloud "SELECT 1"); Write-Host " OK" -ForegroundColor Green
Write-Host "Probando local ($LocalUrl) ..." -NoNewline
[void](Local "SELECT 1"); Write-Host " OK" -ForegroundColor Green

# --- PASO 0: medir tamano real en el cloud ---
$dbList = ($DBs | ForEach-Object { "'$_'" }) -join ','
Write-Host "`n== Tamano real en el cloud (bytes_on_disk = lo comprimido en disco) ==" -ForegroundColor Cyan
Write-Host (Cloud @"
SELECT database, table, formatReadableSize(sum(bytes_on_disk)) AS disk, sum(rows) AS rows
FROM system.parts WHERE active AND database IN ($dbList)
GROUP BY database, table ORDER BY sum(bytes_on_disk) DESC
FORMAT PrettyCompactMonoBlock
"@)
if ($MeasureOnly) { Write-Host "`n(-MeasureOnly) No se descargo nada." -ForegroundColor Yellow; return }

foreach ($db in $DBs) {
  [void](Local "CREATE DATABASE IF NOT EXISTS $db")

  $names = (Cloud @"
SELECT name FROM system.tables
WHERE database='$db' AND engine LIKE '%MergeTree%'
ORDER BY total_bytes FORMAT TabSeparated
"@) -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }

  if ($Tables) { $names = $names | Where-Object { $Tables -contains $_ } }
  if (-not $names) { Write-Host "Sin tablas que sincronizar en '$db'." -ForegroundColor Yellow; continue }

  foreach ($t in $names) {
    Write-Host "`n== $db.$t ==" -ForegroundColor Cyan

    # 1) esquema exacto desde el cloud
    $ddl = Cloud "SELECT create_table_query FROM system.tables WHERE database='$db' AND name='$t' FORMAT TabSeparatedRaw"
    $ddl = $ddl -replace '^CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS '
    [void](Local $ddl)

    # 2) conteos
    $rc = [int64](Cloud "SELECT count() FROM $db.$t")
    $lc = [int64](Local "SELECT count() FROM $db.$t")
    if (-not $Force -and $lc -eq $rc -and $rc -gt 0) {
      Write-Host "ya sincronizada ($lc filas) -> salto" -ForegroundColor Green
      continue
    }

    # 3) plan de trozos
    [void](Local "TRUNCATE TABLE $db.$t")
    $K = [int][math]::Max(1, [math]::Ceiling([double]$rc / $RowsPerChunk))
    $tmp = Join-Path $TempDir "regis_${db}_${t}.native"

    if ($K -le 1) {
      Write-Host "copiando $rc filas (de una)..." -ForegroundColor Gray
      Copy-Chunk $db $t "" $tmp
    }
    else {
      # decidir estrategia segun la llave de orden
      $skey = (Cloud "SELECT sorting_key FROM system.tables WHERE database='$db' AND name='$t'").Trim()
      $rangeCol = $null
      if ($skey -and ($skey -notmatch ',')) {
        $type = (Cloud "SELECT type FROM system.columns WHERE database='$db' AND table='$t' AND name='$skey'").Trim()
        if ($type -match '^U?Int(8|16|32|64|128|256)$') { $rangeCol = $skey }
      }

      if ($rangeCol) {
        # cortes por cuantiles (filas parejas) y lectura por indice
        $probs  = (1..($K - 1) | ForEach-Object { [math]::Round($_ / $K, 6) }) -join ','
        $qraw   = (Cloud "SELECT quantiles($probs)($rangeCol) FROM $db.$t FORMAT TabSeparatedRaw").Trim('[', ']', ' ')
        $bounds = @($qraw -split ',' | ForEach-Object { [int64][math]::Round([double]$_) })
        Write-Host "copiando $rc filas en $K trozos por RANGO de $rangeCol..." -ForegroundColor Gray
        for ($i = 0; $i -lt $K; $i++) {
          if ($i -eq 0)            { $where = "WHERE $rangeCol < $($bounds[0])" }
          elseif ($i -eq $K - 1)   { $where = "WHERE $rangeCol >= $($bounds[$K - 2])" }
          else                     { $where = "WHERE $rangeCol >= $($bounds[$i - 1]) AND $rangeCol < $($bounds[$i])" }
          Write-Host "  trozo $($i + 1)/$K" -ForegroundColor DarkGray
          Copy-Chunk $db $t $where $tmp
        }
      }
      else {
        Write-Host "copiando $rc filas en $K trozos por HASH de ($skey)..." -ForegroundColor Gray
        for ($i = 0; $i -lt $K; $i++) {
          $where = "WHERE cityHash64($skey) % $K = $i"
          Write-Host "  trozo $($i + 1)/$K" -ForegroundColor DarkGray
          Copy-Chunk $db $t $where $tmp
        }
      }
    }
    Remove-Item $tmp -ErrorAction SilentlyContinue

    # 4) verificar
    $lc2 = [int64](Local "SELECT count() FROM $db.$t")
    if ($lc2 -eq $rc) { Write-Host "cloud=$rc local=$lc2 -> OK" -ForegroundColor Green }
    else { Write-Host "cloud=$rc local=$lc2 -> DESAJUSTE" -ForegroundColor Red }
  }
}

Write-Host "`nSincronizacion terminada." -ForegroundColor Cyan
