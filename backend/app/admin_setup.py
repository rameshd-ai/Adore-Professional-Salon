import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.admin_forms import SAL_SITE_SETTINGS_FORM_REV
from app.admin_patch import GlamrAdmin
from app.admin_views import ALL_VIEWS
from app.config import get_settings
from app.database import engine

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_log = logging.getLogger("uvicorn.error")


def admin_model_attr(obj: Any, attr: str) -> str:
    """Jinja helper: safe getattr for showing current uploaded path/filename on edit forms."""
    if obj is None or not attr:
        return ""
    v = getattr(obj, attr, None)
    if v is None:
        return ""
    return str(v).strip()


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        s = get_settings()
        if username == s.admin_username and password == s.admin_password:
            request.session.update({"admin_ok": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin_ok"))


def mount_admin(app: FastAPI) -> None:
    settings = get_settings()
    try:
        import app.admin_forms as admin_forms

        _log.info(
            "SQLAdmin: templates dir=%s admin_forms=%s rev=%s",
            _TEMPLATES_DIR.resolve(),
            Path(admin_forms.__file__).resolve(),
            SAL_SITE_SETTINGS_FORM_REV,
        )
    except Exception as exc:
        _log.warning("SQLAdmin: could not log template/form paths: %s", exc)

    auth = AdminAuth(secret_key=settings.session_secret)
    admin = GlamrAdmin(
        app,
        engine,
        authentication_backend=auth,
        title="Adore Professional Salon",
        templates_dir=str(_TEMPLATES_DIR),
    )
    admin.templates.env.globals["sal_site_settings_form_rev"] = SAL_SITE_SETTINGS_FORM_REV
    admin.templates.env.globals["admin_model_attr"] = admin_model_attr
    for view in ALL_VIEWS:
        admin.add_view(view)
