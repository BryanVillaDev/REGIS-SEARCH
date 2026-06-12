"""Parsing y ranking de nombres para los jobs de busqueda masiva.

Este modulo es puro (no toca ClickHouse) para poder testearlo facil.

La idea central: el ranking es *independiente del orden* de los tokens.
Aunque la entrada venga como "PEREZ GOMEZ JUAN" o "JUAN PEREZ GOMEZ", se
compara el conjunto de tokens contra el conjunto de tokens del registro,
asi no dependemos de adivinar que token es apellido y cual es nombre.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

# Particulas que casi nunca distinguen a una persona: pesan menos al rankear
# y nunca se usan para anclar la consulta a ClickHouse.
PARTICLES = {
    "DE",
    "DEL",
    "LA",
    "LAS",
    "LOS",
    "SAN",
    "SANTA",
    "Y",
    "DI",
    "DA",
    "DOS",
    "DAS",
    "VAN",
    "VON",
    "MC",
    "MAC",
    "EL",
}

PARTICLE_WEIGHT = 0.3
MIN_ANCHOR_LEN = 3
MAX_ANCHOR_TOKENS = 4

# Cualquier separador de columnas distinto al espacio (el espacio separa
# tokens *dentro* de una misma columna / nombre completo).
_COLUMN_DELIMITERS = ["\t", ";", "|", ","]


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_token(value: str) -> str:
    """Mayuscula, sin tildes, solo letras y la enie."""
    cleaned = strip_accents(value).upper()
    cleaned = re.sub(r"[^A-ZÑ]", "", cleaned)
    return cleaned


def tokenize(value: str | None) -> list[str]:
    if not value:
        return []
    tokens = [normalize_token(part) for part in value.split()]
    return [token for token in tokens if token]


def _detect_delimiter(line: str) -> str | None:
    for delimiter in _COLUMN_DELIMITERS:
        if delimiter in line:
            return delimiter
    return None


def split_columns(line: str) -> list[str]:
    delimiter = _detect_delimiter(line)
    if delimiter is None:
        return [line.strip()] if line.strip() else []
    return [part.strip() for part in line.split(delimiter) if part.strip()]


@dataclass
class NameQuery:
    """Una fila de entrada ya parseada."""

    raw: str
    tokens: list[str] = field(default_factory=list)
    apellidos: list[str] = field(default_factory=list)
    nombres: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return bool(self.tokens)


def parse_name_line(raw: str) -> NameQuery:
    """Convierte una linea de entrada en tokens + un split apellidos/nombres.

    El split apellidos/nombres es "mejor esfuerzo" y solo se usa para mostrar;
    el ranking usa ``tokens`` y es independiente del orden.
    """
    columns = split_columns(raw)
    ncols = len(columns)

    if ncols >= 4:
        apellidos = tokenize(columns[0])[:1] + tokenize(columns[1])[:1]
        nombres = tokenize(columns[2])[:1] + tokenize(columns[3])[:1]
    elif ncols == 2:
        # Convencion: primera columna apellidos, segunda nombres.
        apellidos = tokenize(columns[0])[:2]
        nombres = tokenize(columns[1])[:2]
    else:
        # 1 columna (o 3+ que no calzan): tokenizamos todo el texto y
        # asumimos orden canonico ANI (apellidos primero) solo para mostrar.
        flat = tokenize(" ".join(columns) if columns else raw)
        if len(flat) >= 4:
            apellidos, nombres = flat[:2], flat[2:4]
        elif len(flat) == 3:
            apellidos, nombres = flat[:1], flat[1:3]
        elif len(flat) == 2:
            apellidos, nombres = flat[:1], flat[1:2]
        else:
            apellidos, nombres = [], flat[:1]

    tokens = tokenize(" ".join(columns) if columns else raw)
    return NameQuery(raw=raw.strip(), tokens=tokens, apellidos=apellidos, nombres=nombres)


def parse_name_rows(value: list[str] | str) -> tuple[list[str], int]:
    """Limpia y deduplica las filas de entrada.

    Devuelve (filas_unicas, total_filas_no_vacias). Cada fila unica se guarda
    como texto crudo; el worker la vuelve a parsear con :func:`parse_name_line`.
    """
    if isinstance(value, list):
        raw_lines = value
    else:
        raw_lines = value.splitlines()

    input_count = 0
    seen: set[str] = set()
    rows: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        parsed = parse_name_line(stripped)
        if not parsed.is_valid:
            continue
        input_count += 1
        key = " ".join(sorted(parsed.tokens))
        if key in seen:
            continue
        seen.add(key)
        rows.append(stripped)

    if not rows:
        raise ValueError("Debes enviar al menos un nombre valido")
    return rows, input_count


def select_anchor_tokens(tokens: list[str]) -> list[str]:
    """Tokens distintivos para anclar la consulta a ClickHouse (por apellido).

    Se descartan particulas y tokens muy cortos; se priorizan los mas largos.
    """
    candidates = [token for token in tokens if token not in PARTICLES and len(token) >= MIN_ANCHOR_LEN]
    candidates.sort(key=len, reverse=True)
    if not candidates:
        candidates = sorted(set(tokens), key=len, reverse=True)
    # Mantener orden original entre los seleccionados para estabilidad.
    chosen = set(candidates[:MAX_ANCHOR_TOKENS])
    return [token for token in dict.fromkeys(tokens) if token in chosen]


def _token_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _directional_score(source: list[str], target: list[str]) -> float:
    """Promedio ponderado del mejor match de cada token de ``source`` en ``target``."""
    total_weight = 0.0
    accumulated = 0.0
    for token in source:
        weight = PARTICLE_WEIGHT if token in PARTICLES else 1.0
        best = max((_token_similarity(token, other) for other in target), default=0.0)
        accumulated += weight * best
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return accumulated / total_weight


def score_tokens(input_tokens: list[str], candidate_tokens: list[str]) -> int:
    """Score 0-100 independiente del orden entre dos conjuntos de tokens.

    Combina cobertura (cuanto de la entrada esta en el candidato) y precision
    (cuanto del candidato esta en la entrada) con una media tipo F1, asi castiga
    tanto tokens faltantes como sobrantes.
    """
    if not input_tokens or not candidate_tokens:
        return 0
    coverage = _directional_score(input_tokens, candidate_tokens)
    precision = _directional_score(candidate_tokens, input_tokens)
    if coverage + precision == 0:
        return 0
    f_score = 2 * coverage * precision / (coverage + precision)
    return round(f_score * 100)


def candidate_tokens(apellido1, apellido2, nombre1, nombre2) -> list[str]:
    tokens: list[str] = []
    for part in (apellido1, apellido2, nombre1, nombre2):
        tokens.extend(tokenize(part))
    return tokens


def confidence_label(score: int) -> str:
    if score >= 85:
        return "alta"
    if score >= 70:
        return "media"
    if score >= 50:
        return "baja"
    return "muy baja"


def match_state(best_score: int | None) -> str:
    if best_score is None:
        return "sin_coincidencia"
    if best_score >= 70:
        return "encontrado"
    if best_score >= 50:
        return "revisar"
    return "sin_coincidencia"
