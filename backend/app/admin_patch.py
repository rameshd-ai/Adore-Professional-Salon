"""SQLAdmin fixes for this project (upstream assumes FileField names map to model attributes)."""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any

from sqladmin import Admin
from sqladmin.ajax import QueryAjaxModelLoader
from sqladmin.authentication import login_required
from starlette.datastructures import FormData, UploadFile
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.admin_dashboard import get_dashboard_stats
from app.database import SessionLocal
from app.models import ApiSettings, SiteSettings


class GlamrAdmin(Admin):
    @login_required
    async def index(self, request: Request) -> Response:
        stats = get_dashboard_stats()
        return await self.templates.TemplateResponse(
            request,
            "sqladmin/index.html",
            {"dashboard_stats": stats},
        )

    @login_required
    async def list(self, request: Request) -> Response:
        """Inject API settings companion row + count on Site settings list."""
        await self._list(request)

        model_view = self._find_model_view(request.path_params["identity"])
        pagination = await model_view.list(request)
        pagination.add_pagination_urls(request.url)

        request_page = model_view.validate_page_number(request.query_params.get("page"), 1)

        if request_page > pagination.page:
            return RedirectResponse(
                request.url.include_query_params(page=pagination.page), status_code=302
            )

        context: dict[str, Any] = {"model_view": model_view, "pagination": pagination}
        if model_view.identity == "site-settings":
            pagination.count += 1
            db = SessionLocal()
            try:
                context["api_settings_list_row"] = db.get(ApiSettings, 1)
            finally:
                db.close()

        return await self.templates.TemplateResponse(
            request, model_view.list_template, context
        )

    def site_brand(self) -> SimpleNamespace:
        """Salon name + logo from Site settings (id=1) for header, sidebar, login, and <title>."""
        title = self.title
        logo = self.logo_url
        try:
            db = SessionLocal()
            try:
                row = db.query(SiteSettings).filter(SiteSettings.id == 1).first()
                if row:
                    name = (row.salon_name or "").strip()
                    if name:
                        title = name
                    u = (row.logo_url or "").strip()
                    if u:
                        logo = u
            finally:
                db.close()
        except Exception:
            pass
        return SimpleNamespace(title=title, logo_url=logo)

    async def _handle_form_data(self, request: Request, obj: Any = None) -> FormData:
        """Same as sqladmin.Admin._handle_form_data but safe when `key` is not on the model.

        Content/admin forms use FileFields (e.g. `logo_upload`, `image_upload`) that are not ORM columns.
        Starlette still posts an empty UploadFile for untouched inputs; the stock code
        did `getattr(obj, key)` and raised AttributeError.
        """
        form = await request.form()
        form_data: list[tuple[str, str | UploadFile]] = []
        for key, value in form.multi_items():
            if not isinstance(value, UploadFile):
                form_data.append((key, value))
                continue

            should_clear = form.get(key + "_checkbox")
            empty_upload = len(await value.read(1)) != 1
            await value.seek(0)
            if should_clear:
                form_data.append((key, UploadFile(io.BytesIO(b""))))
            elif empty_upload and obj is not None and getattr(obj, key, None):
                f = getattr(obj, key)
                form_data.append((key, UploadFile(filename=f.name, file=f.open())))
            else:
                form_data.append((key, value))
        return FormData(form_data)

    @login_required
    async def ajax_lookup(self, request: Request) -> Response:
        """Ajax lookup: tolerate missing/blank `term` (stock SQLAdmin returns 400 and breaks Select2)."""

        identity = request.path_params["identity"]
        model_view = self._find_model_view(identity)

        name = request.query_params.get("name")
        term = (request.query_params.get("term") or "").strip()

        refs = getattr(model_view, "_form_ajax_refs", {})
        if not name and len(refs) == 1:
            name = next(iter(refs.keys()))

        if not name:
            raise HTTPException(status_code=400)

        try:
            loader: QueryAjaxModelLoader = model_view._form_ajax_refs[name]
        except KeyError as exc:
            raise HTTPException(status_code=400) from exc

        if not term:
            return JSONResponse({"results": []})

        data = [loader.format(m) for m in await loader.get_list(term)]
        return JSONResponse({"results": data})
