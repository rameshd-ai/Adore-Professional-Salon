from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class SiteSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    salon_name: str
    logo_url: str
    phone: str
    email: str
    hours_line: str
    address: str
    map_lat: str
    map_lng: str
    discount_banner_html: str
    discount_book_link_label: str
    facebook_url: str
    instagram_url: str
    twitter_url: str
    footer_tagline: str
    about_subtitle: str
    about_heading: str
    about_para1: str
    about_para2: str
    about_main_image: str
    about_secondary_image: str
    about_years_badge: str
    menu_preview_image: str
    cta_bg_image: str


class HeroSlideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    background_image: str
    tagline: str
    title_line1: str
    title_line2_italic: str
    show_contact_block: bool
    primary_button_label: str
    primary_button_url: str
    secondary_button_label: str
    secondary_button_url: str
    sort_order: int


class ServiceCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    image_url: str
    description: str
    sort_order: int
    is_active: bool
    reference_url: str = ""


class ServiceOut(BaseModel):
    id: int
    category_id: int
    category: str
    title: str
    slug: str
    short_description: str
    image_url: str
    price_from: str
    sort_order: int


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    name: str
    description: str
    price: str
    sort_order: int


class GalleryImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    caption: str
    sort_order: int


class BlogPostListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    excerpt: str
    image_url: str
    author_name: str
    category: str
    published_at: datetime


class BlogPostDetailOut(BlogPostListOut):
    body: str


class TestimonialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote: str
    author_name: str
    subtitle: str
    sort_order: int


class BookingCreate(BaseModel):
    name: str
    phone: str
    service: str = ""
    preferred_date: date | None = None


class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    subject: str = ""
    message: str
