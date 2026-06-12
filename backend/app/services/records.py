from typing import Any

from app.core.clickhouse import get_clickhouse_client
from app.models.schemas import (
    ContactInfo,
    LocationInfo,
    NameSearchItem,
    NameSearchResponse,
    RecordDetail,
)
from app.services.formatting import (
    location_code,
    make_full_name,
    normalize_name,
    serialize_value,
)


IDENTITY_FIELDS = [
    "ANINuip",
    "ANIApellido1",
    "ANIApellido2",
    "ANINombre1",
    "ANINombre2",
    "ANIFchNacimiento",
    "ANISexo",
    "ANIDireccion",
    "ANITelefono",
    "ANIFchExpedicion",
]


def _rows_as_dicts(result: Any) -> list[dict[str, Any]]:
    return [
        {column: serialize_value(value) for column, value in zip(result.column_names, row)}
        for row in result.result_rows
    ]


def _fetch_locations(codes: set[str | None]) -> dict[str, LocationInfo]:
    clean_codes = sorted(code for code in codes if code)
    if not clean_codes:
        return {}
    client = get_clickhouse_client()
    result = client.query(
        """
        SELECT cod, ciudad, depto
        FROM ani.lugares
        WHERE cod IN {codes:Array(String)}
        """,
        parameters={"codes": clean_codes},
    )
    locations: dict[str, LocationInfo] = {}
    for cod, ciudad, depto in result.result_rows:
        locations[str(cod)] = LocationInfo(code=str(cod), ciudad=ciudad, depto=depto)
    return locations


def get_record_detail(aninuip: int) -> RecordDetail | None:
    client = get_clickhouse_client()
    result = client.query(
        "SELECT * FROM ani.ani_fin WHERE ANINuip = {aninuip:Int64} LIMIT 1",
        parameters={"aninuip": int(aninuip)},
    )
    rows = _rows_as_dicts(result)
    if not rows:
        return None

    raw = rows[0]
    location_keys = {
        "nacimiento": location_code(raw.get("LUGIdNacimiento")),
        "residencia": location_code(raw.get("LUGIdResidencia")),
        "expedicion": location_code(raw.get("LUGIdExpedicion")),
    }
    locations_by_code = _fetch_locations(set(location_keys.values()))
    contacts = get_contacts(aninuip)
    full_name = make_full_name(
        raw.get("ANINombre1"),
        raw.get("ANINombre2"),
        raw.get("ANIApellido1"),
        raw.get("ANIApellido2"),
    )

    identity = {field: raw.get(field) for field in IDENTITY_FIELDS if field in raw}

    return RecordDetail(
        aninuip=int(raw["ANINuip"]),
        full_name=full_name,
        identity=identity,
        locations={
            key: locations_by_code.get(code) if code else None
            for key, code in location_keys.items()
        },
        contacts=contacts,
        raw=raw,
    )


def get_contacts(aninuip: int) -> list[ContactInfo]:
    client = get_clickhouse_client()
    result = client.query(
        """
        SELECT cedula, cel, nombre, dir, ciud
        FROM ani.claro2017
        WHERE cedula = {cedula:String}
        LIMIT 20
        """,
        parameters={"cedula": str(aninuip)},
    )
    return [
        ContactInfo(cedula=cedula, cel=cel, nombre=nombre, dir=dir, ciud=ciud)
        for cedula, cel, nombre, dir, ciud in result.result_rows
    ]


def search_by_name(
    *,
    apellido1: str | None,
    apellido2: str | None,
    nombre1: str | None,
    nombre2: str | None,
    mode: str,
    limit: int,
    offset: int,
) -> NameSearchResponse:
    if mode not in {"prefix", "exact"}:
        raise ValueError("El modo debe ser 'prefix' o 'exact'")

    safe_limit = max(1, min(int(limit), 200))
    safe_offset = max(0, int(offset))
    values = {
        "apellido1": normalize_name(apellido1),
        "apellido2": normalize_name(apellido2),
        "nombre1": normalize_name(nombre1),
        "nombre2": normalize_name(nombre2),
    }
    if not any(values.values()):
        raise ValueError("Debes indicar al menos un apellido o nombre")

    field_map = {
        "apellido1": "ANIApellido1",
        "apellido2": "ifNull(ANIApellido2, '')",
        "nombre1": "ANINombre1",
        "nombre2": "ifNull(ANINombre2, '')",
    }
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": safe_limit + 1, "offset": safe_offset}

    for key, value in values.items():
        if not value:
            continue
        parameters[key] = value
        if mode == "exact":
            conditions.append(f"{field_map[key]} = {{{key}:String}}")
        else:
            conditions.append(f"startsWith({field_map[key]}, {{{key}:String}})")

    where_clause = " AND ".join(conditions)
    client = get_clickhouse_client()
    result = client.query(
        f"""
        SELECT
            ANINuip,
            ANIApellido1,
            ANIApellido2,
            ANINombre1,
            ANINombre2,
            ANIFchNacimiento,
            ANISexo,
            LUGIdNacimiento
        FROM ani.ani_fin
        WHERE {where_clause}
        ORDER BY ANIApellido1, ANIApellido2, ANINombre1, ANINombre2, ANINuip
        LIMIT {{limit:UInt32}} OFFSET {{offset:UInt32}}
        """,
        parameters=parameters,
    )

    fetched = result.result_rows
    visible_rows = fetched[:safe_limit]
    codes = {location_code(row[7]) for row in visible_rows}
    locations_by_code = _fetch_locations(codes)

    items = [
        NameSearchItem(
            aninuip=int(row[0]),
            apellido1=row[1],
            apellido2=row[2],
            nombre1=row[3],
            nombre2=row[4],
            fecha_nacimiento=serialize_value(row[5]),
            sexo=row[6],
            full_name=make_full_name(row[3], row[4], row[1], row[2]),
            lugar_nacimiento=locations_by_code.get(location_code(row[7])),
        )
        for row in visible_rows
    ]
    return NameSearchResponse(
        items=items,
        limit=safe_limit,
        offset=safe_offset,
        has_more=len(fetched) > safe_limit,
    )
