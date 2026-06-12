from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.core.clickhouse import get_clickhouse_client


@dataclass(frozen=True)
class UserRecord:
    id: UUID
    username: str
    password_hash: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


def _row_to_user(row: tuple) -> UserRecord:
    return UserRecord(
        id=UUID(str(row[0])),
        username=row[1],
        password_hash=row[2],
        role=row[3],
        is_active=bool(row[4]),
        created_at=row[5],
        updated_at=row[6],
    )


def get_user_by_username(username: str) -> UserRecord | None:
    client = get_clickhouse_client()
    result = client.query(
        """
        SELECT id, username, password_hash, role, is_active, created_at, updated_at
        FROM app.regis_users FINAL
        WHERE username = {username:String}
        LIMIT 1
        """,
        parameters={"username": username.strip()},
    )
    if not result.result_rows:
        return None
    return _row_to_user(result.result_rows[0])


def create_user(username: str, password_hash: str, role: str = "operator") -> UserRecord:
    client = get_clickhouse_client()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user_id = uuid4()
    clean_username = username.strip()
    client.insert(
        "app.regis_users",
        [[str(user_id), clean_username, password_hash, role, 1, now, now]],
        column_names=[
            "id",
            "username",
            "password_hash",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ],
    )
    return UserRecord(
        id=user_id,
        username=clean_username,
        password_hash=password_hash,
        role=role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
