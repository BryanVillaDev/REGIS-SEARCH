from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    id: UUID
    username: str
    role: str
    is_active: bool

    @classmethod
    def from_record(cls, record: Any) -> "UserPublic":
        return cls(
            id=record.id,
            username=record.username,
            role=record.role,
            is_active=record.is_active,
        )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class LocationInfo(BaseModel):
    code: str | None = None
    ciudad: str | None = None
    depto: str | None = None


class ContactInfo(BaseModel):
    cedula: str
    cel: str | None = None
    nombre: str | None = None
    dir: str | None = None
    ciud: str | None = None


class RecordDetail(BaseModel):
    aninuip: int
    full_name: str
    identity: dict[str, Any]
    locations: dict[str, LocationInfo | None]
    contacts: list[ContactInfo]
    raw: dict[str, Any]


class PinCombinationsResponse(BaseModel):
    cedula: int
    lista: list[str]


class NameSearchItem(BaseModel):
    aninuip: int
    apellido1: str
    apellido2: str | None = None
    nombre1: str
    nombre2: str | None = None
    full_name: str
    fecha_nacimiento: str | None = None
    sexo: str | None = None
    lugar_nacimiento: LocationInfo | None = None


class NameSearchResponse(BaseModel):
    items: list[NameSearchItem]
    limit: int
    offset: int
    has_more: bool


class BulkCedulasRequest(BaseModel):
    cedulas: list[str] | str = Field(description="Lista de cedulas o texto separado por saltos, comas o espacios")


class BulkNombresRequest(BaseModel):
    nombres: list[str] | str = Field(
        description=(
            "Lista de nombres o texto con un nombre por linea. Cada linea puede venir en "
            "1 columna (nombre completo), 2 columnas (apellidos | nombres) o 4 columnas "
            "(apellido1 | apellido2 | nombre1 | nombre2), separadas por tab, ';', '|' o ','."
        )
    )


class JobPublic(BaseModel):
    id: UUID
    kind: str
    status: str
    input_count: int
    unique_count: int
    processed_count: int
    result_count: int
    error: str | None = None
    has_csv: bool = False
    has_xlsx: bool = False
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
