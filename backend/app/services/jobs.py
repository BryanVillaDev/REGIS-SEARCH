import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from openpyxl import Workbook

from app.core.clickhouse import get_clickhouse_client
from app.core.config import settings
from app.models.schemas import JobPublic
from app.services.formatting import location_code, make_full_name, parse_cedulas, serialize_value
from app.services.records import _fetch_locations
from app.services.users import UserRecord


@dataclass
class JobRecord:
    id: UUID
    user_id: UUID
    username: str
    kind: str
    status: str
    input_count: int
    unique_count: int
    processed_count: int
    result_count: int
    error: str | None
    export_csv_path: str | None
    export_xlsx_path: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    def public(self) -> JobPublic:
        return JobPublic(
            id=self.id,
            kind=self.kind,
            status=self.status,
            input_count=self.input_count,
            unique_count=self.unique_count,
            processed_count=self.processed_count,
            result_count=self.result_count,
            error=self.error,
            has_csv=bool(self.export_csv_path),
            has_xlsx=bool(self.export_xlsx_path),
            created_at=self.created_at,
            updated_at=self.updated_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
        )


JOB_COLUMNS = [
    "id",
    "user_id",
    "username",
    "kind",
    "status",
    "input_count",
    "unique_count",
    "processed_count",
    "result_count",
    "error",
    "export_csv_path",
    "export_xlsx_path",
    "created_at",
    "updated_at",
    "started_at",
    "finished_at",
]

EXPORT_COLUMNS = [
    "cedula",
    "estado",
    "apellido1",
    "apellido2",
    "nombre1",
    "nombre2",
    "nombre_completo",
    "fecha_nacimiento",
    "sexo",
    "nacimiento_ciudad",
    "nacimiento_depto",
    "residencia_ciudad",
    "residencia_depto",
    "expedicion_ciudad",
    "expedicion_depto",
]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _row_to_job(row: tuple) -> JobRecord:
    return JobRecord(
        id=UUID(str(row[0])),
        user_id=UUID(str(row[1])),
        username=row[2],
        kind=row[3],
        status=row[4],
        input_count=int(row[5]),
        unique_count=int(row[6]),
        processed_count=int(row[7]),
        result_count=int(row[8]),
        error=row[9],
        export_csv_path=row[10],
        export_xlsx_path=row[11],
        created_at=row[12],
        updated_at=row[13],
        started_at=row[14],
        finished_at=row[15],
    )


def _insert_job(job: JobRecord) -> None:
    client = get_clickhouse_client()
    client.insert(
        "app.regis_search_jobs",
        [
            [
                str(job.id),
                str(job.user_id),
                job.username,
                job.kind,
                job.status,
                job.input_count,
                job.unique_count,
                job.processed_count,
                job.result_count,
                job.error,
                job.export_csv_path,
                job.export_xlsx_path,
                job.created_at,
                job.updated_at,
                job.started_at,
                job.finished_at,
            ]
        ],
        column_names=JOB_COLUMNS,
    )


def _update_job(job: JobRecord, **changes) -> JobRecord:
    updated = JobRecord(**{**job.__dict__, **changes, "updated_at": _now()})
    _insert_job(updated)
    return updated


def create_cedulas_job(cedulas_input: list[str] | str, user: UserRecord) -> JobPublic:
    cedulas, input_count = parse_cedulas(cedulas_input)
    now = _now()
    job = JobRecord(
        id=uuid4(),
        user_id=user.id,
        username=user.username,
        kind="cedulas",
        status="queued",
        input_count=input_count,
        unique_count=len(cedulas),
        processed_count=0,
        result_count=0,
        error=None,
        export_csv_path=None,
        export_xlsx_path=None,
        created_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
    )
    client = get_clickhouse_client()
    client.insert(
        "app.regis_search_job_inputs",
        [[str(job.id), cedula] for cedula in cedulas],
        column_names=["job_id", "cedula"],
    )
    _insert_job(job)
    return job.public()


def list_jobs(user: UserRecord, limit: int = 50) -> list[JobPublic]:
    client = get_clickhouse_client()
    user_filter = "" if user.role == "admin" else "WHERE user_id = toUUID({user_id:String})"
    result = client.query(
        f"""
        SELECT {", ".join(JOB_COLUMNS)}
        FROM app.regis_search_jobs FINAL
        {user_filter}
        ORDER BY created_at DESC
        LIMIT {{limit:UInt32}}
        """,
        parameters={"user_id": str(user.id), "limit": int(limit)},
    )
    return [_row_to_job(row).public() for row in result.result_rows]


def get_job(job_id: str, user: UserRecord | None = None) -> JobRecord | None:
    client = get_clickhouse_client()
    conditions = ["id = toUUID({job_id:String})"]
    parameters = {"job_id": job_id}
    if user and user.role != "admin":
        conditions.append("user_id = toUUID({user_id:String})")
        parameters["user_id"] = str(user.id)

    result = client.query(
        f"""
        SELECT {", ".join(JOB_COLUMNS)}
        FROM app.regis_search_jobs FINAL
        WHERE {" AND ".join(conditions)}
        LIMIT 1
        """,
        parameters=parameters,
    )
    if not result.result_rows:
        return None
    return _row_to_job(result.result_rows[0])


def get_download_file(job_id: str, user: UserRecord, file_format: str) -> Path | None:
    job = get_job(job_id, user)
    if not job or job.status != "done":
        return None

    file_value = job.export_csv_path if file_format == "csv" else job.export_xlsx_path
    if not file_value:
        return None

    export_root = Path(settings.export_dir).resolve()
    file_path = Path(file_value).resolve()
    if export_root not in file_path.parents and file_path != export_root:
        return None
    if not file_path.exists():
        return None
    return file_path


def claim_next_job() -> JobRecord | None:
    client = get_clickhouse_client()
    result = client.query(
        f"""
        SELECT {", ".join(JOB_COLUMNS)}
        FROM app.regis_search_jobs FINAL
        WHERE status = 'queued'
        ORDER BY created_at
        LIMIT 1
        """
    )
    if not result.result_rows:
        return None
    job = _row_to_job(result.result_rows[0])
    return _update_job(job, status="running", started_at=_now(), error=None)


def process_job(job: JobRecord) -> JobRecord:
    if job.kind != "cedulas":
        return _update_job(
            job,
            status="failed",
            error=f"Tipo de job no soportado: {job.kind}",
            finished_at=_now(),
        )

    try:
        return _process_cedulas_job(job)
    except Exception as exc:  # noqa: BLE001 - worker must persist failures.
        return _update_job(
            job,
            status="failed",
            error=str(exc),
            finished_at=_now(),
        )


def _fetch_job_cedulas(job_id: UUID) -> list[int]:
    client = get_clickhouse_client()
    result = client.query(
        """
        SELECT cedula
        FROM app.regis_search_job_inputs
        WHERE job_id = toUUID({job_id:String})
        ORDER BY cedula
        """,
        parameters={"job_id": str(job_id)},
    )
    return [int(row[0]) for row in result.result_rows]


def _query_records(cedulas: list[int]) -> dict[int, dict]:
    client = get_clickhouse_client()
    result = client.query(
        """
        SELECT
            ANINuip,
            ANIApellido1,
            ANIApellido2,
            ANINombre1,
            ANINombre2,
            ANIFchNacimiento,
            ANISexo,
            LUGIdNacimiento,
            LUGIdResidencia,
            LUGIdExpedicion
        FROM ani.ani_fin
        WHERE ANINuip IN {cedulas:Array(Int64)}
        """,
        parameters={"cedulas": cedulas},
    )
    records: dict[int, dict] = {}
    for row in result.result_rows:
        records[int(row[0])] = {
            "ANINuip": int(row[0]),
            "ANIApellido1": row[1],
            "ANIApellido2": row[2],
            "ANINombre1": row[3],
            "ANINombre2": row[4],
            "ANIFchNacimiento": serialize_value(row[5]),
            "ANISexo": row[6],
            "LUGIdNacimiento": row[7],
            "LUGIdResidencia": row[8],
            "LUGIdExpedicion": row[9],
        }
    return records


def _export_row(cedula: int, record: dict | None, locations: dict[str, object]) -> dict:
    if not record:
        return {
            "cedula": cedula,
            "estado": "no_encontrado",
            "apellido1": "",
            "apellido2": "",
            "nombre1": "",
            "nombre2": "",
            "nombre_completo": "",
            "fecha_nacimiento": "",
            "sexo": "",
            "nacimiento_ciudad": "",
            "nacimiento_depto": "",
            "residencia_ciudad": "",
            "residencia_depto": "",
            "expedicion_ciudad": "",
            "expedicion_depto": "",
        }

    nacimiento = locations.get(location_code(record.get("LUGIdNacimiento")))
    residencia = locations.get(location_code(record.get("LUGIdResidencia")))
    expedicion = locations.get(location_code(record.get("LUGIdExpedicion")))
    return {
        "cedula": cedula,
        "estado": "encontrado",
        "apellido1": record.get("ANIApellido1") or "",
        "apellido2": record.get("ANIApellido2") or "",
        "nombre1": record.get("ANINombre1") or "",
        "nombre2": record.get("ANINombre2") or "",
        "nombre_completo": make_full_name(
            record.get("ANINombre1"),
            record.get("ANINombre2"),
            record.get("ANIApellido1"),
            record.get("ANIApellido2"),
        ),
        "fecha_nacimiento": record.get("ANIFchNacimiento") or "",
        "sexo": record.get("ANISexo") or "",
        "nacimiento_ciudad": getattr(nacimiento, "ciudad", "") if nacimiento else "",
        "nacimiento_depto": getattr(nacimiento, "depto", "") if nacimiento else "",
        "residencia_ciudad": getattr(residencia, "ciudad", "") if residencia else "",
        "residencia_depto": getattr(residencia, "depto", "") if residencia else "",
        "expedicion_ciudad": getattr(expedicion, "ciudad", "") if expedicion else "",
        "expedicion_depto": getattr(expedicion, "depto", "") if expedicion else "",
    }


def _process_cedulas_job(job: JobRecord) -> JobRecord:
    export_dir = Path(settings.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    csv_path = export_dir / f"cedulas-{job.id}.csv"
    xlsx_path = export_dir / f"cedulas-{job.id}.xlsx"

    cedulas = _fetch_job_cedulas(job.id)
    processed = 0
    found = 0
    create_xlsx = len(cedulas) <= settings.xlsx_max_rows
    workbook = Workbook(write_only=True) if create_xlsx else None
    worksheet = workbook.create_sheet("Resultados") if workbook else None
    if worksheet:
        worksheet.append(EXPORT_COLUMNS)

    current_job = job
    with csv_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()

        chunk_size = max(1, settings.bulk_chunk_size)
        for index in range(0, len(cedulas), chunk_size):
            chunk = cedulas[index : index + chunk_size]
            records = _query_records(chunk)
            codes: set[str | None] = set()
            for record in records.values():
                codes.add(location_code(record.get("LUGIdNacimiento")))
                codes.add(location_code(record.get("LUGIdResidencia")))
                codes.add(location_code(record.get("LUGIdExpedicion")))
            locations = _fetch_locations(codes)

            for cedula in chunk:
                record = records.get(cedula)
                if record:
                    found += 1
                row = _export_row(cedula, record, locations)
                writer.writerow(row)
                if worksheet:
                    worksheet.append([row[column] for column in EXPORT_COLUMNS])

            processed += len(chunk)
            current_job = _update_job(
                current_job,
                processed_count=processed,
                result_count=found,
            )

    xlsx_file_value = None
    if workbook:
        workbook.save(xlsx_path)
        xlsx_file_value = str(xlsx_path)

    return _update_job(
        current_job,
        status="done",
        processed_count=processed,
        result_count=found,
        export_csv_path=str(csv_path),
        export_xlsx_path=xlsx_file_value,
        finished_at=_now(),
    )
