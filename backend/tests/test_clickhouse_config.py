from app.core import clickhouse


def test_http_url_without_port_uses_http_default(monkeypatch):
    monkeypatch.setattr(clickhouse.settings, "clickhouse_url", "http://example.test")
    monkeypatch.setattr(clickhouse.settings, "clickhouse_secure", False)

    kwargs = clickhouse._client_kwargs()

    assert kwargs["host"] == "example.test"
    assert kwargs["port"] == 80


def test_host_without_scheme_uses_clickhouse_default(monkeypatch):
    monkeypatch.setattr(clickhouse.settings, "clickhouse_url", "example.test")
    monkeypatch.setattr(clickhouse.settings, "clickhouse_secure", False)

    kwargs = clickhouse._client_kwargs()

    assert kwargs["host"] == "example.test"
    assert kwargs["port"] == 8123
