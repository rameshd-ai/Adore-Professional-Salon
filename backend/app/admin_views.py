from __future__ import annotations

import asyncio
from html import escape
from pathlib import Path
from typing import Any

from markupsafe import Markup
from wtforms import StringField
from wtforms.fields.core import UnboundField
from wtforms.validators import Length, Optional as OptionalValidator
from sqlalchemy import inspect as sa_inspect, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.sql import Select
from sqladmin import BaseView, ModelView, expose
from sqladmin.fields import AjaxSelectField, FileField
from sqladmin.filters import (
    AllUniqueStringValuesFilter,
    BooleanFilter,
    ForeignKeyFilter,
    StaticValuesFilter,
)
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.admin_forms import GalleryImageForm, ServiceCategoryForm, SiteSettingsForm
from app.admin_uploads import merge_upload_into_url_field
from app.config import get_settings
from app.database import SessionLocal
from app.models import (
    ApiSettings,
    BlogPost,
    BookingInquiry,
    ContactMessage,
    Customer,
    CustomerServiceVisit,
    GalleryImage,
    HeroSlide,
    SalonProduct,
    Service,
    ServiceCategory,
    SiteSettings,
    StockMovement,
    Stylist,
    Testimonial,
    WhatsAppInboxMessage,
)
from app.visit_pricing import sum_visit_services
from app.whatsapp_meta import (
    normalize_whatsapp_recipient,
    send_image_message,
    send_text_message,
)


def _thumb(url: str | None, h: int = 44) -> Markup | str:
    if not url or not str(url).strip():
        return "—"
    u = str(url).strip()
    return Markup(
        f'<img src="{escape(u)}" class="admin-thumb" style="max-height:{h}px;max-width:72px;'
        f'object-fit:cover;border-radius:6px;vertical-align:middle" loading="lazy" alt="">'
    )


def _trunc(s: str | None, n: int = 72) -> str:
    if not s:
        return "—"
    t = str(s).replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _visit_merge_new_customer(data: dict) -> dict:
    """If no customer is selected, create or reuse by phone from new_* fields; strip extras from data."""
    data = dict(data)
    new_name = (data.pop("new_customer_full_name", None) or "").strip()
    new_phone = (data.pop("new_customer_phone", None) or "").strip()
    cust = data.get("customer")
    has_customer = cust not in (None, "")

    if has_customer:
        return data

    if new_phone:
        display_name = new_name or "Walk-in"
        db = SessionLocal()
        try:
            existing = db.scalars(
                select(Customer).where(Customer.phone == new_phone).limit(1)
            ).first()
            if existing is not None:
                data["customer"] = existing.id
            else:
                c = Customer(full_name=display_name, phone=new_phone)
                db.add(c)
                db.commit()
                db.refresh(c)
                data["customer"] = c.id
        finally:
            db.close()
        return data

    if new_name:
        raise ValueError("Enter a phone number for the new customer, or select an existing customer above.")

    raise ValueError("Select a customer, or enter a phone number to add someone new.")


def _visit_recompute_amount_from_services(data: dict) -> dict:
    """Set amount_charged from the sum of selected catalog service prices (server-side)."""
    data = dict(data)
    raw = data.get("visit_services")
    if not raw:
        return data
    db = SessionLocal()
    try:
        rows: list[Service] = []
        if isinstance(raw, list):
            for x in raw:
                if isinstance(x, Service):
                    rows.append(x)
                elif x not in (None, ""):
                    o = db.get(Service, int(x))
                    if o is not None:
                        rows.append(o)
        if not rows:
            return data
        _, formatted = sum_visit_services(rows)
        data["amount_charged"] = formatted
    finally:
        db.close()
    return data


def _visit_service_display(m: CustomerServiceVisit, a: object) -> str:
    try:
        if m.service is not None:
            return m.service.title
    except DetachedInstanceError:
        pass
    if m.custom_service_name:
        return m.custom_service_name
    if m.service_id:
        return f"Catalog #{m.service_id}"
    return "—"


def _visit_services_line_display(m: CustomerServiceVisit, a: object) -> str:
    try:
        items = m.visit_services
        if items:
            return _trunc(", ".join(i.title for i in items), 88)
    except DetachedInstanceError:
        pass
    return _visit_service_display(m, a)


class ApiSettingsAdmin(ModelView, model=ApiSettings):
    """Singleton row edited from Site settings list (second row). Hidden from sidebar."""

    name = "API settings"
    name_plural = "API settings"
    icon = "fa fa-key"
    category = "API"
    category_icon = "fa fa-plug"
    can_delete = False
    can_create = False

    def is_visible(self, request: Request) -> bool:
        return False
    column_list = [
        ApiSettings.id,
        ApiSettings.whatsapp_enabled,
        ApiSettings.whatsapp_phone_number_id,
        ApiSettings.whatsapp_api_version,
    ]
    column_details_list = [
        ApiSettings.whatsapp_enabled,
        ApiSettings.whatsapp_access_token,
        ApiSettings.whatsapp_phone_number_id,
        ApiSettings.whatsapp_api_version,
        ApiSettings.whatsapp_webhook_verify_token,
        ApiSettings.whatsapp_app_secret,
        ApiSettings.integration_notes,
    ]
    form_columns = [
        ApiSettings.whatsapp_enabled,
        ApiSettings.whatsapp_access_token,
        ApiSettings.whatsapp_phone_number_id,
        ApiSettings.whatsapp_api_version,
        ApiSettings.whatsapp_webhook_verify_token,
        ApiSettings.whatsapp_app_secret,
        ApiSettings.integration_notes,
    ]
    column_labels = {
        ApiSettings.whatsapp_phone_number_id: "WhatsApp phone number ID",
        ApiSettings.whatsapp_access_token: "WhatsApp access token",
        ApiSettings.integration_notes: "Notes",
        ApiSettings.whatsapp_webhook_verify_token: "Webhook verify token",
        ApiSettings.whatsapp_app_secret: "App secret (webhook signature)",
    }
    form_args = {
        "whatsapp_enabled": {
            "description": "When off, the WhatsApp broadcast page refuses to send.",
        },
        "whatsapp_access_token": {
            "description": "Meta permanent access token (WhatsApp Business Platform). Never exposed on the public API.",
        },
        "whatsapp_phone_number_id": {
            "description": "From Meta App Dashboard → WhatsApp → API setup (Phone number ID).",
        },
        "whatsapp_api_version": {
            "description": "Graph API version label, e.g. v22.0",
        },
        "whatsapp_webhook_verify_token": {
            "description": "Same value you enter in Meta → WhatsApp → Configuration → Webhook → Verify token. Callback URL: https://YOUR_DOMAIN/webhooks/whatsapp",
        },
        "whatsapp_app_secret": {
            "description": "Optional. Meta App → Settings → Basic → App secret. If set, POST webhooks must include a valid X-Hub-Signature-256 header.",
        },
        "integration_notes": {
            "description": "Internal notes only.",
        },
    }
    page_size = 5


class WhatsAppBroadcastView(BaseView):
    name = "Send offers"
    icon = "fa fa-whatsapp"
    category = "WhatsApp"
    category_icon = "fa fa-whatsapp"

    @expose("/whatsapp-broadcast", methods=["GET", "POST"], identity="whatsapp_broadcast")
    async def broadcast(self, request: Request) -> Response:
        db = SessionLocal()
        try:
            customers = db.scalars(
                select(Customer)
                .where(Customer.is_active.is_(True))
                .order_by(Customer.full_name)
            ).all()
            api = db.get(ApiSettings, 1)
        finally:
            db.close()

        recipient_rows = [
            {
                "id": c.id,
                "label": f"{(c.full_name or '').strip() or '—'} — {c.phone.strip()}",
            }
            for c in customers
            if (c.phone or "").strip()
        ]
        api_ok = bool(
            api
            and api.whatsapp_enabled
            and (api.whatsapp_access_token or "").strip()
            and (api.whatsapp_phone_number_id or "").strip()
        )

        results: list[dict[str, Any]] | None = None
        error_msg: str | None = None

        if request.method == "POST":
            form = await request.form()
            ids_raw = form.getlist("customer_ids")
            try:
                ids = [int(x) for x in ids_raw if str(x).strip().isdigit()]
            except (TypeError, ValueError):
                ids = []
            message = (form.get("message") or "").strip()
            image_url = (form.get("image_url") or "").strip()

            if not api_ok:
                error_msg = "Configure WhatsApp in API → API settings (enable + token + phone number ID)."
            elif not ids:
                error_msg = "Select at least one customer with a phone number."
            elif not message and not image_url:
                error_msg = "Enter a message and/or an image URL."
            else:
                db2 = SessionLocal()
                try:
                    targets = db2.scalars(select(Customer).where(Customer.id.in_(ids))).all()
                finally:
                    db2.close()
                token = (api.whatsapp_access_token or "").strip()
                pid = (api.whatsapp_phone_number_id or "").strip()
                ver = (api.whatsapp_api_version or "").strip() or "v22.0"
                results = []
                for cust in targets:
                    phone_raw = (cust.phone or "").strip()
                    name = (cust.full_name or "").strip() or f"#{cust.id}"
                    to = normalize_whatsapp_recipient(phone_raw)
                    if not to:
                        results.append(
                            {
                                "name": name,
                                "phone": phone_raw,
                                "ok": False,
                                "detail": "Could not normalize phone (need 10+ digits / country code).",
                            }
                        )
                        continue
                    if image_url:
                        r = send_image_message(
                            access_token=token,
                            phone_number_id=pid,
                            api_version=ver,
                            to_digits=to,
                            image_https_url=image_url,
                            caption=message,
                        )
                    else:
                        r = send_text_message(
                            access_token=token,
                            phone_number_id=pid,
                            api_version=ver,
                            to_digits=to,
                            body=message,
                        )
                    results.append(
                        {
                            "name": name,
                            "phone": phone_raw,
                            "ok": r.ok,
                            "detail": "Sent" if r.ok else r.detail,
                        }
                    )
                    await asyncio.sleep(0.12)

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/whatsapp_broadcast.html",
            {
                "title": "WhatsApp broadcast",
                "subtitle": "Uses Meta WhatsApp Cloud API. Promotional blasts may require approved message templates.",
                "recipient_rows": recipient_rows,
                "api_configured": api_ok,
                "results": results,
                "error_msg": error_msg,
            },
        )


class WhatsAppInboxAdmin(ModelView, model=WhatsAppInboxMessage):
    name = "WhatsApp inbox"
    name_plural = "WhatsApp inbox"
    icon = "fa fa-inbox"
    category = "WhatsApp"
    category_icon = "fa fa-whatsapp"
    can_create = False
    can_delete = True
    column_list = [
        WhatsAppInboxMessage.id,
        WhatsAppInboxMessage.created_at,
        WhatsAppInboxMessage.from_wa_id,
        WhatsAppInboxMessage.profile_name,
        WhatsAppInboxMessage.customer,
        WhatsAppInboxMessage.body_text,
        WhatsAppInboxMessage.message_type,
        WhatsAppInboxMessage.is_read,
    ]
    column_formatters = {WhatsAppInboxMessage.body_text: lambda m, a: _trunc(m.body_text, 72)}
    column_searchable_list = [
        WhatsAppInboxMessage.from_wa_id,
        WhatsAppInboxMessage.profile_name,
        WhatsAppInboxMessage.body_text,
        WhatsAppInboxMessage.wa_message_id,
    ]
    column_sortable_list = [
        WhatsAppInboxMessage.created_at,
        WhatsAppInboxMessage.is_read,
        WhatsAppInboxMessage.from_wa_id,
    ]
    column_default_sort = [(WhatsAppInboxMessage.created_at, True)]
    column_labels = {
        WhatsAppInboxMessage.from_wa_id: "WhatsApp ID",
        WhatsAppInboxMessage.body_text: "Message",
        WhatsAppInboxMessage.is_read: "Read",
    }
    column_filters = [BooleanFilter(WhatsAppInboxMessage.is_read, title="Read")]
    details_template = "sqladmin/whatsapp_inbox_details.html"
    column_details_list = [
        WhatsAppInboxMessage.wa_message_id,
        WhatsAppInboxMessage.created_at,
        WhatsAppInboxMessage.from_wa_id,
        WhatsAppInboxMessage.profile_name,
        WhatsAppInboxMessage.customer,
        WhatsAppInboxMessage.message_type,
        WhatsAppInboxMessage.body_text,
        WhatsAppInboxMessage.raw_payload,
        WhatsAppInboxMessage.is_read,
    ]
    form_columns = [WhatsAppInboxMessage.is_read]

    def list_query(self, request: Request) -> Select:
        return select(self.model).options(selectinload(WhatsAppInboxMessage.customer))

    def form_edit_query(self, request: Request) -> Select:
        stmt = super().form_edit_query(request)
        return stmt.options(selectinload(WhatsAppInboxMessage.customer))


class SiteSettingsAdmin(ModelView, model=SiteSettings):
    """Singleton (id=1): salon name, phone, email, address, hours, about copy, images. Open list → Edit row 1."""
    name = "Site settings"
    name_plural = "Site settings"
    icon = "fa fa-sliders"
    category = "Site"
    category_icon = "fa fa-globe"
    form = SiteSettingsForm
    form_rules = [
        "salon_name",
        "logo_upload",
        "phone",
        "email",
        "hours_line",
        "address",
        "map_lat",
        "map_lng",
        "discount_banner_html",
        "discount_book_link_label",
        "facebook_url",
        "instagram_url",
        "twitter_url",
        "footer_tagline",
        "about_subtitle",
        "about_heading",
        "about_para1",
        "about_para2",
        "about_main_upload",
        "about_secondary_upload",
        "about_years_badge",
        "menu_preview_upload",
        "cta_bg_upload",
    ]
    edit_template = "sqladmin/site_settings_edit.html"
    list_template = "sqladmin/site_settings_list.html"
    column_list = [
        SiteSettings.id,
        SiteSettings.logo_url,
        SiteSettings.salon_name,
        SiteSettings.phone,
        SiteSettings.email,
        SiteSettings.hours_line,
    ]
    column_formatters = {
        SiteSettings.logo_url: lambda m, a: _thumb(m.logo_url, 36),
        SiteSettings.id: lambda m, a: Markup(
            '<span class="text-gray-800 fw-semibold">Website &amp; salon</span>'
        ),
    }
    column_searchable_list = [SiteSettings.salon_name, SiteSettings.email, SiteSettings.phone]
    column_sortable_list = [SiteSettings.salon_name]
    column_default_sort = [(SiteSettings.id, False)]
    column_labels = {
        SiteSettings.id: "API And Site Settings",
        SiteSettings.salon_name: "Salon",
        SiteSettings.hours_line: "Hours",
        SiteSettings.logo_url: "Logo",
    }
    can_delete = False
    can_create = False
    page_size = 5

    async def update_model(self, request: Request, pk: str, data: dict) -> object:
        data = dict(data)
        data = await self._merge_logo_upload(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="about_main_upload",
            url_key="about_main_image",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        await merge_upload_into_url_field(
            data,
            upload_key="about_secondary_upload",
            url_key="about_secondary_image",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        await merge_upload_into_url_field(
            data,
            upload_key="menu_preview_upload",
            url_key="menu_preview_image",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        await merge_upload_into_url_field(
            data,
            upload_key="cta_bg_upload",
            url_key="cta_bg_image",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        # Drop non-column keys (e.g. FileFields). SQLAdmin's _set_attributes_sync
        # crashes on falsy extras: it reads column.nullable when column is None.
        col_keys = {c.key for c in sa_inspect(SiteSettings).mapper.columns}
        data = {k: v for k, v in data.items() if k in col_keys}
        return await super().update_model(request, pk, data)

    async def _merge_logo_upload(self, data: dict) -> dict:
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="logo_upload",
            url_key="logo_url",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        return data


class ServiceCategoryAdmin(ModelView, model=ServiceCategory):
    name = "Category"
    name_plural = "Categories"
    icon = "fa fa-folder-open"
    category = "Content"
    category_icon = "fa fa-image"
    form = ServiceCategoryForm
    form_rules = [
        "name",
        "slug",
        "image_upload",
        "description",
        "reference_url",
        "sort_order",
        "is_active",
    ]
    column_list = [
        ServiceCategory.id,
        ServiceCategory.image_url,
        ServiceCategory.name,
        ServiceCategory.slug,
        ServiceCategory.reference_url,
        ServiceCategory.sort_order,
        ServiceCategory.is_active,
    ]
    column_formatters = {ServiceCategory.image_url: lambda m, a: _thumb(m.image_url)}
    column_searchable_list = [ServiceCategory.name, ServiceCategory.slug, ServiceCategory.description]
    column_sortable_list = [ServiceCategory.sort_order, ServiceCategory.name, ServiceCategory.is_active]
    column_default_sort = [(ServiceCategory.sort_order, False), (ServiceCategory.id, False)]
    column_labels = {
        ServiceCategory.image_url: "Preview",
        ServiceCategory.description: "Description",
        ServiceCategory.reference_url: "Source URL",
    }
    column_filters = [BooleanFilter(ServiceCategory.is_active, title="Active")]

    async def insert_model(self, request: Request, data: dict) -> Any:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="image_upload",
            url_key="image_url",
            upload_root=root,
            keep_existing_if_empty=False,
        )
        cols = {c.key for c in sa_inspect(ServiceCategory).mapper.columns}
        data = {k: v for k, v in data.items() if k in cols}
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="image_upload",
            url_key="image_url",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        cols = {c.key for c in sa_inspect(ServiceCategory).mapper.columns}
        data = {k: v for k, v in data.items() if k in cols}
        return await super().update_model(request, pk, data)


class HeroSlideAdmin(ModelView, model=HeroSlide):
    name = "Hero slide"
    name_plural = "Hero slides"
    icon = "fa fa-image"
    category = "Content"
    category_icon = "fa fa-image"
    form_columns = [
        HeroSlide.tagline,
        HeroSlide.title_line1,
        HeroSlide.title_line2_italic,
        HeroSlide.show_contact_block,
        HeroSlide.primary_button_label,
        HeroSlide.primary_button_url,
        HeroSlide.secondary_button_label,
        HeroSlide.secondary_button_url,
        HeroSlide.sort_order,
        HeroSlide.is_active,
    ]
    form_rules = [
        "background_upload",
        "tagline",
        "title_line1",
        "title_line2_italic",
        "show_contact_block",
        "primary_button_label",
        "primary_button_url",
        "secondary_button_label",
        "secondary_button_url",
        "sort_order",
        "is_active",
    ]
    column_list = [
        HeroSlide.id,
        HeroSlide.background_image,
        HeroSlide.tagline,
        HeroSlide.title_line1,
        HeroSlide.sort_order,
        HeroSlide.is_active,
    ]
    column_formatters = {
        HeroSlide.background_image: lambda m, a: _thumb(m.background_image, 40),
    }
    column_searchable_list = [HeroSlide.tagline, HeroSlide.title_line1]
    column_sortable_list = [HeroSlide.sort_order, HeroSlide.id, HeroSlide.is_active]
    column_default_sort = [(HeroSlide.sort_order, False), (HeroSlide.id, False)]
    column_labels = {
        HeroSlide.background_image: "Preview",
        HeroSlide.title_line2_italic: "Title line 2 (italic)",
    }
    column_filters = [BooleanFilter(HeroSlide.is_active, title="Active")]

    async def scaffold_form(self, rules: list[str] | None = None) -> type:
        Base = await super().scaffold_form(rules)
        return type(
            "HeroSlideAdminForm",
            (Base,),
            {
                "background_upload": FileField(
                    "Upload slide image",
                    description="JPG, PNG, WebP or GIF.",
                ),
            },
        )

    async def insert_model(self, request: Request, data: dict) -> Any:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="background_upload",
            url_key="background_image",
            upload_root=root,
            keep_existing_if_empty=False,
        )
        if not (data.get("background_image") or "").strip():
            raise ValueError("Upload a slide image.")
        cols = {c.key for c in sa_inspect(HeroSlide).mapper.columns}
        data = {k: v for k, v in data.items() if k in cols}
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="background_upload",
            url_key="background_image",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        cols = {c.key for c in sa_inspect(HeroSlide).mapper.columns}
        data = {k: v for k, v in data.items() if k in cols}
        return await super().update_model(request, pk, data)


class ServiceAdmin(ModelView, model=Service):
    name = "Service"
    name_plural = "Services"
    icon = "fa fa-scissors"
    category = "Content"
    form_rules = [
        "service_category",
        "title",
        "slug",
        "short_description",
        "image_upload",
        "price_from",
        "sort_order",
        "is_active",
    ]
    column_list = [
        Service.id,
        Service.image_url,
        Service.service_category,
        Service.title,
        Service.slug,
        Service.price_from,
        Service.sort_order,
        Service.is_active,
    ]
    column_formatters = {Service.image_url: lambda m, a: _thumb(m.image_url)}
    column_searchable_list = [Service.title, Service.slug, Service.short_description]
    column_sortable_list = [Service.sort_order, Service.title, Service.is_active]
    column_default_sort = [(Service.sort_order, False), (Service.id, False)]
    column_labels = {
        Service.image_url: "Preview",
        Service.price_from: "From",
        Service.short_description: "Description",
        Service.service_category: "Category",
    }
    # Use relationship (not category_id) so the form gets a proper select/dropdown of categories.
    form_columns = [
        Service.service_category,
        Service.title,
        Service.slug,
        Service.short_description,
        Service.price_from,
        Service.sort_order,
        Service.is_active,
    ]
    form_args = {
        "service_category": {
            "description": "Choose the main category (Hair, Skin, …). Manage the list under Content → Categories.",
        },
        "slug": {
            "description": "Imported Essence rows use slugs like e-<id>. Avoid changing synced slugs.",
        },
    }
    column_filters = [
        BooleanFilter(Service.is_active, title="Active"),
        ForeignKeyFilter(
            Service.category_id,
            ServiceCategory.name,
            ServiceCategory,
            title="Category",
        ),
    ]

    async def scaffold_form(self, rules: list[str] | None = None) -> type:
        Base = await super().scaffold_form(rules)
        return type(
            "ServiceAdminForm",
            (Base,),
            {
                "image_upload": FileField(
                    "Upload image",
                    description="JPG, PNG, WebP or GIF. Optional.",
                ),
            },
        )

    async def insert_model(self, request: Request, data: dict) -> Any:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="image_upload",
            url_key="image_url",
            upload_root=root,
            keep_existing_if_empty=False,
        )
        cols = {c.key for c in sa_inspect(Service).mapper.columns}
        data = {k: v for k, v in data.items() if k in cols}
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="image_upload",
            url_key="image_url",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        cols = {c.key for c in sa_inspect(Service).mapper.columns}
        data = {k: v for k, v in data.items() if k in cols}
        return await super().update_model(request, pk, data)


class GalleryImageAdmin(ModelView, model=GalleryImage):
    name = "Gallery image"
    name_plural = "Gallery"
    icon = "fa fa-photo"
    category = "Content"
    form = GalleryImageForm
    form_rules = ["upload", "caption", "sort_order", "is_active"]
    column_list = [
        GalleryImage.id,
        GalleryImage.image_url,
        GalleryImage.caption,
        GalleryImage.sort_order,
        GalleryImage.is_active,
    ]
    column_formatters = {GalleryImage.image_url: lambda m, a: _thumb(m.image_url)}
    column_searchable_list = [GalleryImage.caption, GalleryImage.image_url]
    column_sortable_list = [GalleryImage.sort_order, GalleryImage.is_active]
    column_default_sort = [(GalleryImage.sort_order, False), (GalleryImage.id, False)]
    column_labels = {
        GalleryImage.image_url: "Preview",
    }
    column_filters = [BooleanFilter(GalleryImage.is_active, title="Active")]

    async def insert_model(self, request: Request, data: dict) -> object:
        data = dict(data)
        data = await self._merge_upload(data)
        if not (data.get("image_url") or "").strip():
            raise ValueError("Upload an image file.")
        gcols = {c.key for c in sa_inspect(GalleryImage).mapper.columns}
        data = {k: v for k, v in data.items() if k in gcols}
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: str, data: dict) -> object:
        data = dict(data)
        data = await self._merge_upload(data, allow_keep_empty=True)
        gcols = {c.key for c in sa_inspect(GalleryImage).mapper.columns}
        data = {k: v for k, v in data.items() if k in gcols}
        return await super().update_model(request, pk, data)

    async def _merge_upload(self, data: dict, *, allow_keep_empty: bool = False) -> dict:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="upload",
            url_key="image_url",
            upload_root=root,
            keep_existing_if_empty=allow_keep_empty,
        )
        return data


class BlogPostAdmin(ModelView, model=BlogPost):
    name = "Blog post"
    name_plural = "Blog posts"
    icon = "fa fa-rss"
    category = "Content"
    form_columns = [
        BlogPost.title,
        BlogPost.slug,
        BlogPost.excerpt,
        BlogPost.body,
        BlogPost.author_name,
        BlogPost.category,
        BlogPost.published_at,
        BlogPost.is_published,
    ]
    form_rules = [
        "title",
        "slug",
        "excerpt",
        "image_upload",
        "body",
        "author_name",
        "category",
        "published_at",
        "is_published",
    ]
    column_list = [
        BlogPost.id,
        BlogPost.image_url,
        BlogPost.title,
        BlogPost.slug,
        BlogPost.excerpt,
        BlogPost.category,
        BlogPost.author_name,
        BlogPost.published_at,
        BlogPost.is_published,
    ]
    column_formatters = {
        BlogPost.image_url: lambda m, a: _thumb(m.image_url, 40),
        BlogPost.excerpt: lambda m, a: _trunc(m.excerpt, 56),
    }
    column_searchable_list = [BlogPost.title, BlogPost.slug, BlogPost.excerpt, BlogPost.author_name]
    column_sortable_list = [BlogPost.published_at, BlogPost.title, BlogPost.is_published]
    column_default_sort = [(BlogPost.published_at, True)]
    column_labels = {
        BlogPost.image_url: "Preview",
        BlogPost.is_published: "Published",
    }
    column_filters = [
        BooleanFilter(BlogPost.is_published, title="Published"),
        AllUniqueStringValuesFilter(BlogPost.category, title="Category"),
    ]

    async def scaffold_form(self, rules: list[str] | None = None) -> type:
        Base = await super().scaffold_form(rules)
        return type(
            "BlogPostAdminForm",
            (Base,),
            {
                "image_upload": FileField(
                    "Upload cover image",
                    description="JPG, PNG, WebP or GIF. Optional.",
                ),
            },
        )

    async def insert_model(self, request: Request, data: dict) -> Any:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="image_upload",
            url_key="image_url",
            upload_root=root,
            keep_existing_if_empty=False,
        )
        cols = {c.key for c in sa_inspect(BlogPost).mapper.columns}
        data = {k: v for k, v in data.items() if k in cols}
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        data = dict(data)
        root = Path(get_settings().upload_dir)
        await merge_upload_into_url_field(
            data,
            upload_key="image_upload",
            url_key="image_url",
            upload_root=root,
            keep_existing_if_empty=True,
        )
        cols = {c.key for c in sa_inspect(BlogPost).mapper.columns}
        data = {k: v for k, v in data.items() if k in cols}
        return await super().update_model(request, pk, data)


class TestimonialAdmin(ModelView, model=Testimonial):
    name = "Testimonial"
    name_plural = "Testimonials"
    icon = "fa fa-quote-left"
    category = "Content"
    column_list = [
        Testimonial.id,
        Testimonial.quote,
        Testimonial.author_name,
        Testimonial.subtitle,
        Testimonial.sort_order,
        Testimonial.is_active,
    ]
    column_formatters = {Testimonial.quote: lambda m, a: _trunc(m.quote, 96)}
    column_searchable_list = [Testimonial.author_name, Testimonial.quote, Testimonial.subtitle]
    column_sortable_list = [Testimonial.sort_order, Testimonial.is_active]
    column_default_sort = [(Testimonial.sort_order, False)]
    column_filters = [BooleanFilter(Testimonial.is_active, title="Active")]


class BookingInquiryAdmin(ModelView, model=BookingInquiry):
    name = "Booking"
    name_plural = "Bookings"
    icon = "fa fa-calendar"
    category = "Inbox"
    category_icon = "fa fa-inbox"
    column_list = [
        BookingInquiry.id,
        BookingInquiry.name,
        BookingInquiry.phone,
        BookingInquiry.service,
        BookingInquiry.preferred_date,
        BookingInquiry.created_at,
    ]
    column_searchable_list = [BookingInquiry.name, BookingInquiry.phone, BookingInquiry.service]
    column_sortable_list = [BookingInquiry.created_at, BookingInquiry.preferred_date]
    column_default_sort = [(BookingInquiry.created_at, True)]
    can_create = False
    column_labels = {BookingInquiry.preferred_date: "Preferred date"}
    column_filters = [AllUniqueStringValuesFilter(BookingInquiry.service, title="Service")]


class ContactMessageAdmin(ModelView, model=ContactMessage):
    name = "Contact message"
    name_plural = "Contact messages"
    icon = "fa fa-envelope"
    category = "Inbox"
    column_list = [
        ContactMessage.id,
        ContactMessage.name,
        ContactMessage.email,
        ContactMessage.subject,
        ContactMessage.message,
        ContactMessage.created_at,
        ContactMessage.is_read,
    ]
    column_formatters = {ContactMessage.message: lambda m, a: _trunc(m.message, 64)}
    column_searchable_list = [
        ContactMessage.name,
        ContactMessage.email,
        ContactMessage.subject,
        ContactMessage.message,
    ]
    column_sortable_list = [ContactMessage.created_at, ContactMessage.is_read]
    column_default_sort = [(ContactMessage.created_at, True)]
    can_create = False
    column_labels = {ContactMessage.is_read: "Read"}
    column_filters = [BooleanFilter(ContactMessage.is_read, title="Read")]


class CustomerAdmin(ModelView, model=Customer):
    name = "Customer"
    name_plural = "Customers"
    icon = "fa fa-user"
    category = "Customers"
    category_icon = "fa fa-address-book"
    column_list = [
        Customer.id,
        Customer.full_name,
        Customer.phone,
        Customer.email,
        Customer.visit_count,
        Customer.is_active,
        Customer.created_at,
    ]
    column_details_list = [
        Customer.full_name,
        Customer.phone,
        Customer.email,
        Customer.notes,
        Customer.visit_count,
        Customer.is_active,
        Customer.created_at,
    ]
    column_labels = {Customer.visit_count: "Visits"}
    column_searchable_list = [Customer.full_name, Customer.phone, Customer.email, Customer.notes]
    column_sortable_list = [
        Customer.full_name,
        Customer.created_at,
        Customer.is_active,
        Customer.phone,
        Customer.visit_count,
    ]
    column_default_sort = [(Customer.created_at, True)]
    column_filters = [BooleanFilter(Customer.is_active, title="Active")]
    form_excluded_columns = [Customer.visits]


class StylistAdmin(ModelView, model=Stylist):
    name = "Stylist"
    name_plural = "Stylists"
    icon = "fa fa-user-tie"
    category = "Stylists"
    category_icon = "fa fa-user-tie"
    column_list = [
        Stylist.id,
        Stylist.full_name,
        Stylist.phone,
        Stylist.is_active,
        Stylist.sort_order,
        Stylist.created_at,
    ]
    column_searchable_list = [Stylist.full_name, Stylist.phone, Stylist.notes]
    column_sortable_list = [Stylist.sort_order, Stylist.full_name, Stylist.is_active, Stylist.created_at]
    column_default_sort = [(Stylist.sort_order, False), (Stylist.full_name, False)]
    column_filters = [BooleanFilter(Stylist.is_active, title="Active")]
    form_columns = [
        Stylist.full_name,
        Stylist.phone,
        Stylist.notes,
        Stylist.sort_order,
        Stylist.is_active,
    ]
    form_args = {
        "full_name": {"description": "Shown in service history and visit forms."},
        "sort_order": {"description": "Lower numbers appear first in dropdowns."},
    }


class CustomerServiceVisitAdmin(ModelView, model=CustomerServiceVisit):
    name = "Service visit"
    name_plural = "Service history"
    icon = "fa fa-scissors"
    category = "Customers"
    category_icon = "fa fa-address-book"
    create_template = "sqladmin/visit_create.html"
    edit_template = "sqladmin/visit_edit.html"
    column_list = [
        CustomerServiceVisit.id,
        CustomerServiceVisit.customer,
        CustomerServiceVisit.visit_services,
        CustomerServiceVisit.visit_date,
        CustomerServiceVisit.stylist,
        CustomerServiceVisit.amount_charged,
        CustomerServiceVisit.notes,
        CustomerServiceVisit.created_at,
    ]
    column_formatters = {
        CustomerServiceVisit.visit_services: _visit_services_line_display,
        CustomerServiceVisit.notes: lambda m, a: _trunc(m.notes, 56),
    }
    column_labels = {
        CustomerServiceVisit.visit_services: "Services billed",
        CustomerServiceVisit.stylist: "Stylist",
        CustomerServiceVisit.amount_charged: "Amount",
    }
    column_searchable_list = [
        CustomerServiceVisit.notes,
        CustomerServiceVisit.custom_service_name,
    ]
    column_sortable_list = [
        CustomerServiceVisit.visit_date,
        CustomerServiceVisit.created_at,
        CustomerServiceVisit.amount_charged,
    ]
    column_default_sort = [(CustomerServiceVisit.visit_date, True), (CustomerServiceVisit.id, True)]
    form_columns = [
        CustomerServiceVisit.customer,
        CustomerServiceVisit.visit_services,
        CustomerServiceVisit.custom_service_name,
        CustomerServiceVisit.visit_date,
        CustomerServiceVisit.stylist,
        CustomerServiceVisit.amount_charged,
        CustomerServiceVisit.notes,
    ]
    form_ajax_refs = {
        "customer": {
            "fields": ("phone",),
            # Tuple ("id",) breaks SQLAlchemy 2 order_by(); use real column objects in a list.
            "order_by": [Customer.id],
        },
    }
    form_args = {
        "customer": {
            "validators": [OptionalValidator()],
            "description": "Search by phone digits, or skip and enter phone under “New customer” (name optional).",
        },
        "visit_services": {
            "description": "Catalog services (Content → Services). Search and pick multiple; amount updates automatically.",
        },
        "custom_service_name": {
            "description": "Optional extra or non-menu work (e.g. bespoke treatment).",
        },
        "stylist": {
            "validators": [OptionalValidator()],
            "description": "Who performed the services — manage the list in the Stylists menu.",
        },
        "amount_charged": {
            "description": "Filled from selected services; you can adjust before saving.",
        },
    }
    form_widget_args = {
        "visit_services": {"size": 12},
    }
    column_filters = [
        ForeignKeyFilter(
            CustomerServiceVisit.customer_id,
            Customer.full_name,
            Customer,
            title="Customer",
        ),
    ]

    def list_query(self, request: Request) -> Select:
        return select(self.model).options(
            selectinload(CustomerServiceVisit.service),
            selectinload(CustomerServiceVisit.stylist),
            selectinload(CustomerServiceVisit.visit_services),
        )

    def form_edit_query(self, request: Request) -> Select:
        stmt = super().form_edit_query(request)
        return stmt.options(
            selectinload(CustomerServiceVisit.service),
            selectinload(CustomerServiceVisit.stylist),
            selectinload(CustomerServiceVisit.visit_services),
        )

    async def scaffold_form(self, rules: list[str] | None = None) -> type:
        Base = await super().scaffold_form(rules)
        # SQLAdmin's form_overrides call Field(**kwargs) without `loader`; we patch the
        # stock UnboundField so allow_blank=True while keeping positional loader.
        ub = Base.customer
        if not getattr(ub, "args", ()):
            raise RuntimeError("Customer field missing AJAX loader")
        loader = ub.args[0]
        customer_kw = dict(ub.kwargs)
        customer_kw["allow_blank"] = True
        customer_field = UnboundField(AjaxSelectField, loader, **customer_kw)

        def validate_visit(form: Any, extra_validators: Any = None) -> bool:
            if not Base.validate(form, extra_validators):
                return False
            cid = form.customer.data
            nn = (form.new_customer_full_name.data or "").strip()
            np = (form.new_customer_phone.data or "").strip()
            if cid not in (None, ""):
                return True
            if np:
                return True
            if nn:
                form.new_customer_phone.errors.append(
                    "Phone is required for a new customer (or pick someone in the search above)."
                )
            else:
                form.customer.errors.append(
                    "Select a customer, or enter a phone number under “New customer” below."
                )
            return False

        return type(
            "CustomerServiceVisitForm",
            (Base,),
            {
                "customer": customer_field,
                "new_customer_full_name": StringField(
                    "New customer name (optional)",
                    validators=[OptionalValidator(), Length(max=160)],
                    description="Leave blank to save as “Walk-in”. Phone below is required if you do not pick someone above.",
                ),
                "new_customer_phone": StringField(
                    "New customer phone (required if new)",
                    validators=[OptionalValidator(), Length(max=64)],
                    description="Required when adding someone who is not in the search. Same digits you will use to find them later.",
                    render_kw={"placeholder": "e.g. 9876543210"},
                ),
                "validate": validate_visit,
            },
        )

    async def insert_model(self, request: Request, data: dict) -> Any:
        data = _visit_merge_new_customer(data)
        data = _visit_recompute_amount_from_services(data)
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        data = _visit_merge_new_customer(data)
        data = _visit_recompute_amount_from_services(data)
        return await super().update_model(request, pk, data)


class SalonProductAdmin(ModelView, model=SalonProduct):
    name = "Product"
    name_plural = "Products"
    icon = "fa fa-box"
    category = "Products & stock"
    category_icon = "fa fa-cubes"
    column_list = [
        SalonProduct.id,
        SalonProduct.name,
        SalonProduct.sku,
        SalonProduct.category,
        SalonProduct.unit,
        SalonProduct.quantity_on_hand,
        SalonProduct.reorder_level,
        SalonProduct.unit_cost,
        SalonProduct.is_active,
    ]
    column_searchable_list = [SalonProduct.name, SalonProduct.sku, SalonProduct.category, SalonProduct.notes]
    column_sortable_list = [
        SalonProduct.name,
        SalonProduct.quantity_on_hand,
        SalonProduct.category,
        SalonProduct.is_active,
        SalonProduct.sku,
    ]
    column_default_sort = [(SalonProduct.category, False), (SalonProduct.name, False)]
    column_labels = {
        SalonProduct.unit_cost: "Unit cost",
        SalonProduct.quantity_on_hand: "On hand",
        SalonProduct.reorder_level: "Reorder at",
    }
    column_filters = [
        BooleanFilter(SalonProduct.is_active, title="Active"),
        AllUniqueStringValuesFilter(SalonProduct.category, title="Category"),
    ]


class StockMovementAdmin(ModelView, model=StockMovement):
    name = "Stock movement"
    name_plural = "Stock movements"
    icon = "fa fa-right-left"
    category = "Products & stock"
    category_icon = "fa fa-cubes"
    column_list = [
        StockMovement.id,
        StockMovement.product,
        StockMovement.quantity,
        StockMovement.movement_type,
        StockMovement.note,
        StockMovement.created_at,
    ]
    column_searchable_list = [StockMovement.note]
    column_sortable_list = [StockMovement.created_at, StockMovement.quantity, StockMovement.movement_type]
    column_default_sort = [(StockMovement.created_at, True)]
    column_labels = {
        StockMovement.quantity: "Qty (+ in / − out)",
        StockMovement.movement_type: "Type",
    }
    form_columns = [
        StockMovement.product_id,
        StockMovement.quantity,
        StockMovement.movement_type,
        StockMovement.note,
    ]
    form_args = {
        "quantity": {
            "description": "Positive = stock in; negative = use, sale, or waste.",
        },
        "movement_type": {
            "description": "Typical values: purchase, consumption, adjustment, return.",
        },
    }
    can_edit = False
    can_delete = False
    column_filters = [
        StaticValuesFilter(
            StockMovement.movement_type,
            [
                ("purchase", "Purchase / stock in"),
                ("consumption", "Consumption / use"),
                ("adjustment", "Adjustment"),
                ("return", "Return to supplier"),
            ],
            title="Type",
        ),
    ]

    async def after_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
        if not is_created or not isinstance(model, StockMovement):
            return
        db = SessionLocal()
        try:
            prod = db.get(SalonProduct, model.product_id)
            if prod is not None:
                prod.quantity_on_hand = int(prod.quantity_on_hand) + int(model.quantity)
                db.add(prod)
                db.commit()
        finally:
            db.close()


_WHATSAPP_INBOX_IDENTITY = "whats-app-inbox-message"


class WhatsAppInboxReplyView(BaseView):
    """POST target for sending a reply from the inbox detail page (hidden from menu)."""

    name = "WhatsApp inbox reply"
    icon = "fa fa-reply"

    def is_visible(self, request: Request) -> bool:
        return False

    @expose("/whatsapp-inbox-reply", methods=["POST"], identity="whatsapp_inbox_reply")
    async def post_reply(self, request: Request) -> RedirectResponse:
        form = await request.form()
        pk_raw = (form.get("pk") or "").strip()
        body = (form.get("reply_body") or "").strip()
        list_url = str(request.url_for("admin:list", identity=_WHATSAPP_INBOX_IDENTITY))
        if not pk_raw or not body:
            return RedirectResponse(url=list_url, status_code=303)
        try:
            pk = int(pk_raw)
        except ValueError:
            return RedirectResponse(url=list_url, status_code=303)

        db = SessionLocal()
        try:
            row = db.get(WhatsAppInboxMessage, pk)
            if row is None:
                return RedirectResponse(url=list_url, status_code=303)
            api = db.get(ApiSettings, 1)
            api_ok = bool(
                api
                and api.whatsapp_enabled
                and (api.whatsapp_access_token or "").strip()
                and (api.whatsapp_phone_number_id or "").strip()
            )
            detail_url = request.url_for("admin:details", identity=_WHATSAPP_INBOX_IDENTITY, pk=str(pk))
            if not api_ok:
                u = detail_url.include_query_params(
                    reply_err="Configure WhatsApp in API settings (enable + token + phone number ID)."
                )
                return RedirectResponse(url=str(u), status_code=303)
            to_digits = normalize_whatsapp_recipient(row.from_wa_id)
            if not to_digits:
                u = detail_url.include_query_params(
                    reply_err="Could not use sender WhatsApp ID as a phone number."
                )
                return RedirectResponse(url=str(u), status_code=303)
            token = (api.whatsapp_access_token or "").strip()
            pid = (api.whatsapp_phone_number_id or "").strip()
            ver = (api.whatsapp_api_version or "").strip() or "v22.0"
            r = send_text_message(
                access_token=token,
                phone_number_id=pid,
                api_version=ver,
                to_digits=to_digits,
                body=body,
            )
            if r.ok:
                row.is_read = True
                db.add(row)
                db.commit()
                u = detail_url.include_query_params(reply_ok="1")
            else:
                err = (r.detail or "Send failed")[:220]
                u = detail_url.include_query_params(reply_err=err)
            return RedirectResponse(url=str(u), status_code=303)
        finally:
            db.close()


ALL_VIEWS = (
    WhatsAppInboxReplyView,
    ApiSettingsAdmin,
    WhatsAppBroadcastView,
    WhatsAppInboxAdmin,
    SiteSettingsAdmin,
    HeroSlideAdmin,
    ServiceCategoryAdmin,
    ServiceAdmin,
    GalleryImageAdmin,
    BlogPostAdmin,
    TestimonialAdmin,
    CustomerAdmin,
    StylistAdmin,
    CustomerServiceVisitAdmin,
    SalonProductAdmin,
    StockMovementAdmin,
    BookingInquiryAdmin,
    ContactMessageAdmin,
)
