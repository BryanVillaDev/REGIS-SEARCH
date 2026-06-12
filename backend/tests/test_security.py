from app.core.security import get_password_hash, verify_password


def test_password_hash_roundtrip():
    password_hash = get_password_hash("clave-segura")

    assert password_hash != "clave-segura"
    assert verify_password("clave-segura", password_hash)
    assert not verify_password("otra-clave", password_hash)
