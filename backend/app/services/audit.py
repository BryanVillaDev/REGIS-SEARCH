import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.clickhouse import get_clickhouse_client
from app.services.users import UserRecord


def record_audit(
    *,
    user: UserRecord,
    event: str,
    filters: dict,
    result_count: int,
    status: str,
    duration_ms: int,
    ip: str,
) -> None:
    client = get_clickhouse_client()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    client.insert(
        "app.regis_search_audit",
        [
            [
                str(uuid4()),
                str(user.id),
                user.username,
                event,
                json.dumps(filters, ensure_ascii=True, default=str),
                int(result_count),
                status,
                int(duration_ms),
                ip,
                now,
            ]
        ],
        column_names=[
            "id",
            "user_id",
            "username",
            "event",
            "filters",
            "result_count",
            "status",
            "duration_ms",
            "ip",
            "created_at",
        ],
    )
