from app.core.clickhouse import init_metadata
from app.core.config import settings
from app.core.security import get_password_hash
from app.services.users import create_user, get_user_by_username


def bootstrap_app() -> None:
    init_metadata()
    if settings.bootstrap_admin_user and settings.bootstrap_admin_password:
        existing = get_user_by_username(settings.bootstrap_admin_user)
        if not existing:
            create_user(
                username=settings.bootstrap_admin_user,
                password_hash=get_password_hash(settings.bootstrap_admin_password),
                role="admin",
            )
