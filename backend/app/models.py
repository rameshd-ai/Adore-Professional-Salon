from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Table, Text, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.brand_defaults import (
    DEFAULT_ADDRESS,
    DEFAULT_EMAIL,
    DEFAULT_HOURS_LINE,
    DEFAULT_PHONE,
    DEFAULT_SALON_NAME,
)
from app.database import Base

# Service visits ↔ catalog services billed on one visit (many-to-many)
visit_service_items = Table(
    "customer_service_visit_services",
    Base.metadata,
    Column(
        "visit_id",
        Integer,
        ForeignKey("customer_service_visits.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "service_id",
        Integer,
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class SiteSettings(Base):
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    salon_name: Mapped[str] = mapped_column(String(120), default=DEFAULT_SALON_NAME)
    logo_url: Mapped[str] = mapped_column(String(500), default="")
    phone: Mapped[str] = mapped_column(String(64), default=DEFAULT_PHONE)
    email: Mapped[str] = mapped_column(String(255), default=DEFAULT_EMAIL)
    hours_line: Mapped[str] = mapped_column(String(200), default=DEFAULT_HOURS_LINE)
    address: Mapped[str] = mapped_column(Text, default=DEFAULT_ADDRESS)
    map_lat: Mapped[str] = mapped_column(String(32), default="")
    map_lng: Mapped[str] = mapped_column(String(32), default="")
    discount_banner_html: Mapped[str] = mapped_column(String(500), default="")
    discount_book_link_label: Mapped[str] = mapped_column(String(64), default="Book Now")
    facebook_url: Mapped[str] = mapped_column(String(500), default="")
    instagram_url: Mapped[str] = mapped_column(String(500), default="")
    twitter_url: Mapped[str] = mapped_column(String(500), default="")
    footer_tagline: Mapped[str] = mapped_column(Text, default="")
    about_subtitle: Mapped[str] = mapped_column(String(120), default="Welcome")
    about_heading: Mapped[str] = mapped_column(String(200), default="Your Beauty and Style is Our Passion")
    about_para1: Mapped[str] = mapped_column(Text, default="")
    about_para2: Mapped[str] = mapped_column(Text, default="")
    about_main_image: Mapped[str] = mapped_column(String(500), default="")
    about_secondary_image: Mapped[str] = mapped_column(String(500), default="")
    about_years_badge: Mapped[str] = mapped_column(String(20), default="10+")
    menu_preview_image: Mapped[str] = mapped_column(String(500), default="")
    cta_bg_image: Mapped[str] = mapped_column(String(500), default="")


class ApiSettings(Base):
    """Integrations and API keys (singleton row id=1). Not exposed on the public REST API."""

    __tablename__ = "api_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_access_token: Mapped[str] = mapped_column(Text, default="")
    whatsapp_phone_number_id: Mapped[str] = mapped_column(String(64), default="")
    whatsapp_api_version: Mapped[str] = mapped_column(String(16), default="v22.0")
    integration_notes: Mapped[str] = mapped_column(Text, default="")
    whatsapp_webhook_verify_token: Mapped[str] = mapped_column(String(255), default="")
    whatsapp_app_secret: Mapped[str] = mapped_column(Text, default="")


class WhatsAppInboxMessage(Base):
    """Inbound WhatsApp Cloud API messages (customer → business), stored via webhook."""

    __tablename__ = "whatsapp_inbox_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wa_message_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    from_wa_id: Mapped[str] = mapped_column(String(32), index=True)
    profile_name: Mapped[str] = mapped_column(String(160), default="")
    message_type: Mapped[str] = mapped_column(String(40), default="text")
    body_text: Mapped[str] = mapped_column(Text, default="")
    raw_payload: Mapped[str] = mapped_column(Text, default="")
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped["Customer | None"] = relationship("Customer")


class ServiceCategory(Base):
    """Main menu category (Hair, Skin, …). Services link here via `category_id`."""

    __tablename__ = "service_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reference_url: Mapped[str] = mapped_column(String(500), default="")

    services: Mapped[list["Service"]] = relationship(
        "Service", back_populates="service_category"
    )

    def __str__(self) -> str:
        return self.name or f"Category #{self.id}"


class HeroSlide(Base):
    __tablename__ = "hero_slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    background_image: Mapped[str] = mapped_column(String(500))
    tagline: Mapped[str] = mapped_column(String(200))
    title_line1: Mapped[str] = mapped_column(String(200))
    title_line2_italic: Mapped[str] = mapped_column(String(200), default="")
    show_contact_block: Mapped[bool] = mapped_column(Boolean, default=True)
    primary_button_label: Mapped[str] = mapped_column(String(80), default="Contact Us")
    primary_button_url: Mapped[str] = mapped_column(String(200), default="/contact")
    secondary_button_label: Mapped[str] = mapped_column(String(80), default="")
    secondary_button_url: Mapped[str] = mapped_column(String(200), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    short_description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(500))
    price_from: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)

    service_category: Mapped["ServiceCategory"] = relationship(
        "ServiceCategory", back_populates="services"
    )
    customer_visits: Mapped[list["CustomerServiceVisit"]] = relationship(
        "CustomerServiceVisit", back_populates="service"
    )

    def __str__(self) -> str:
        """Used by SQLAdmin / WTForms for FK and M2M labels (title + price when present)."""
        t = (self.title or "").strip()
        base = t if t else f"Service #{self.id}"
        p = (self.price_from or "").strip()
        if p:
            return f"{base} — {p}"
        return base


class GalleryImage(Base):
    __tablename__ = "gallery_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_url: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str] = mapped_column(String(200), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(120), default="Admin")
    category: Mapped[str] = mapped_column(String(80), default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class Testimonial(Base):
    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(120))
    subtitle: Mapped[str] = mapped_column(String(120), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BookingInquiry(Base):
    __tablename__ = "booking_inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(64))
    service: Mapped[str] = mapped_column(String(120), default="")
    preferred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(200), default="")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class Customer(Base):
    """Salon client profile."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(64), default="", index=True)
    email: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    visits: Mapped[list["CustomerServiceVisit"]] = relationship(
        "CustomerServiceVisit", back_populates="customer", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        p = (self.phone or "").strip()
        n = (self.full_name or "").strip()
        if p and n:
            return f"{p} — {n}"
        return p or n or f"Customer #{self.id}"


class Stylist(Base):
    """Staff member who performed services (linked from service history)."""

    __tablename__ = "stylists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    visits: Mapped[list["CustomerServiceVisit"]] = relationship(
        "CustomerServiceVisit", back_populates="stylist"
    )

    def __str__(self) -> str:
        n = (self.full_name or "").strip()
        return n or f"Stylist #{self.id}"


class CustomerServiceVisit(Base):
    """One completed service for a customer (history)."""

    __tablename__ = "customer_service_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    visit_services: Mapped[list["Service"]] = relationship(
        "Service",
        secondary=visit_service_items,
        lazy="selectin",
    )
    custom_service_name: Mapped[str] = mapped_column(
        String(200), default=""
    )  # when not chosen from catalog (or extra detail)
    visit_date: Mapped[date] = mapped_column(Date, index=True)
    stylist_id: Mapped[int | None] = mapped_column(
        ForeignKey("stylists.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount_charged: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped["Customer"] = relationship("Customer", back_populates="visits")
    stylist: Mapped["Stylist | None"] = relationship("Stylist", back_populates="visits")
    service: Mapped["Service | None"] = relationship("Service", back_populates="customer_visits")


class SalonProduct(Base):
    """Retail / backbar inventory item (color, shampoo, disposables, tools, etc.)."""

    __tablename__ = "salon_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(64), default="", index=True)
    category: Mapped[str] = mapped_column(String(100), default="")
    unit: Mapped[str] = mapped_column(String(32), default="ea")
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement", back_populates="product", cascade="all, delete-orphan"
    )


class StockMovement(Base):
    """Stock in (+) or out (−) against a product; creating a row updates quantity_on_hand."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("salon_products.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    movement_type: Mapped[str] = mapped_column(String(40), default="adjustment")
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["SalonProduct"] = relationship("SalonProduct", back_populates="movements")


# After CustomerServiceVisit exists: count service-history rows per customer (list/detail in admin).
Customer.visit_count = column_property(
    select(func.count(CustomerServiceVisit.id))
    .where(CustomerServiceVisit.customer_id == Customer.id)
    .scalar_subquery()
)
