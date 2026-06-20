import re
from datetime import date, datetime
from typing import Any


def normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().upper().split())
    return cleaned or None


def parse_cedulas(value: list[str] | str) -> tuple[list[int], int]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[\s,;|]+", value)

    input_count = 0
    seen: set[int] = set()
    cedulas: list[int] = []
    for item in raw_items:
        input_count += 1
        digits = re.sub(r"\D+", "", str(item))
        if not digits:
            continue
        cedula = int(digits)
        if cedula <= 0 or cedula in seen:
            continue
        seen.add(cedula)
        cedulas.append(cedula)

    if not cedulas:
        raise ValueError("Debes enviar al menos una cedula valida")
    return cedulas, input_count


def serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def make_full_name(*parts: str | None) -> str:
    return " ".join(part for part in parts if part).strip()


def parse_date(value: Any) -> date | None:
    """Convierte fechas (date/datetime/ISO string) a ``date``; None si no aplica."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    return None


def date_pin_combinations(value: Any) -> dict[str, str]:
    """Devuelve todas las combinaciones de 4 digitos derivadas de una fecha.

    A partir de dia (DD), mes (MM) y anio (YYYY / YY ultimos dos digitos) se
    arman las 7 combinaciones que siempre ocupan exactamente 4 digitos:

    - ``anio``     -> YYYY (anio completo)
    - ``dia_mes``  -> DDMM
    - ``mes_dia``  -> MMDD
    - ``dia_anio`` -> DDYY
    - ``anio_dia`` -> YYDD
    - ``mes_anio`` -> MMYY
    - ``anio_mes`` -> YYMM
    """
    parsed = parse_date(value)
    if parsed is None:
        return {}
    dd = f"{parsed.day:02d}"
    mm = f"{parsed.month:02d}"
    yyyy = f"{parsed.year:04d}"
    yy = yyyy[-2:]
    return {
        "anio": yyyy,
        "dia_mes": dd + mm,
        "mes_dia": mm + dd,
        "dia_anio": dd + yy,
        "anio_dia": yy + dd,
        "mes_anio": mm + yy,
        "anio_mes": yy + mm,
    }


def location_code(value: Any) -> str | None:
    if value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    if number <= 99999:
        return str(number).zfill(5)
    return str((number // 1000) % 100000).zfill(5)
