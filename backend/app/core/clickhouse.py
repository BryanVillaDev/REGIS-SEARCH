from functools import lru_cache
from urllib.parse import urlparse

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.core.config import settings


def _client_kwargs() -> dict:
    parsed = urlparse(settings.clickhouse_url)
    host = parsed.hostname or settings.clickhouse_url
    secure = settings.clickhouse_secure or parsed.scheme == "https"
    if parsed.port:
        port = parsed.port
    elif parsed.scheme in {"http", "https"}:
        port = 443 if secure else 80
    else:
        port = 8443 if secure else 8123
    username = parsed.username or settings.clickhouse_user
    password = parsed.password or settings.clickhouse_password

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "database": settings.clickhouse_database,
        "secure": secure,
        "connect_timeout": settings.query_timeout_seconds,
        "send_receive_timeout": settings.query_timeout_seconds,
    }


@lru_cache(maxsize=1)
def get_clickhouse_client() -> Client:
    return clickhouse_connect.get_client(**_client_kwargs())


def init_metadata() -> None:
    client = get_clickhouse_client()
    client.command("CREATE DATABASE IF NOT EXISTS app")

    client.command(
        """
        CREATE TABLE IF NOT EXISTS app.regis_users
        (
            id UUID,
            username String,
            password_hash String,
            role LowCardinality(String),
            is_active UInt8,
            created_at DateTime,
            updated_at DateTime
        )
        ENGINE = ReplacingMergeTree(updated_at)
        ORDER BY username
        """
    )

    client.command(
        """
        CREATE TABLE IF NOT EXISTS app.regis_search_audit
        (
            id UUID,
            user_id UUID,
            username String,
            event LowCardinality(String),
            filters String,
            result_count UInt64,
            status LowCardinality(String),
            duration_ms UInt64,
            ip String,
            created_at DateTime
        )
        ENGINE = MergeTree
        ORDER BY (created_at, username, event)
        """
    )

    client.command(
        """
        CREATE TABLE IF NOT EXISTS app.regis_search_jobs
        (
            id UUID,
            user_id UUID,
            username String,
            kind LowCardinality(String),
            status LowCardinality(String),
            input_count UInt64,
            unique_count UInt64,
            processed_count UInt64,
            result_count UInt64,
            error Nullable(String),
            export_csv_path Nullable(String),
            export_xlsx_path Nullable(String),
            created_at DateTime,
            updated_at DateTime,
            started_at Nullable(DateTime),
            finished_at Nullable(DateTime)
        )
        ENGINE = ReplacingMergeTree(updated_at)
        ORDER BY id
        """
    )

    client.command(
        """
        CREATE TABLE IF NOT EXISTS app.regis_search_job_inputs
        (
            job_id UUID,
            cedula Int64
        )
        ENGINE = MergeTree
        ORDER BY (job_id, cedula)
        """
    )

    client.command(
        """
        CREATE TABLE IF NOT EXISTS app.regis_search_job_name_inputs
        (
            job_id UUID,
            row_index UInt32,
            raw String
        )
        ENGINE = MergeTree
        ORDER BY (job_id, row_index)
        """
    )
