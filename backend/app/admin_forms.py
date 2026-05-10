from wtforms import BooleanField, Form, IntegerField, StringField, TextAreaField, validators
from wtforms.validators import DataRequired, NumberRange, Optional

from sqladmin.fields import FileField

# Bumped when Site settings image UX changes; surfaced on /health + admin Jinja globals for debugging wrong deploys.
SAL_SITE_SETTINGS_FORM_REV = "v6-upload-only-20260510"


class SiteSettingsForm(Form):
    salon_name = StringField("Salon name", validators=[validators.Length(max=120)])
    logo_upload = FileField(
        "Logo (choose file)",
        description="PNG, JPG, WebP or GIF. Replaces the current logo when you save.",
    )
    phone = StringField("Phone", validators=[validators.Length(max=64)])
    email = StringField("Email", validators=[validators.Length(max=255)])
    hours_line = StringField("Hours line", validators=[validators.Length(max=200)])
    address = TextAreaField("Address")
    map_lat = StringField(
        "Map latitude",
        validators=[Optional(), validators.Length(max=32)],
        description="Optional. Decimal degrees (e.g. 11.659874). Used for Contact page map pin.",
    )
    map_lng = StringField(
        "Map longitude",
        validators=[Optional(), validators.Length(max=32)],
        description="Optional. Decimal degrees (e.g. 92.736025). Pair with latitude.",
    )
    discount_banner_html = StringField(
        "Discount banner HTML",
        validators=[Optional(), validators.Length(max=500)],
    )
    discount_book_link_label = StringField(
        "Discount CTA label",
        validators=[Optional(), validators.Length(max=64)],
    )
    facebook_url = StringField("Facebook URL", validators=[Optional(), validators.Length(max=500)])
    instagram_url = StringField("Instagram URL", validators=[Optional(), validators.Length(max=500)])
    twitter_url = StringField("Twitter URL", validators=[Optional(), validators.Length(max=500)])
    footer_tagline = TextAreaField("Footer tagline")
    about_subtitle = StringField("About subtitle", validators=[validators.Length(max=120)])
    about_heading = StringField("About heading", validators=[validators.Length(max=200)])
    about_para1 = TextAreaField("About paragraph 1")
    about_para2 = TextAreaField("About paragraph 2")
    about_main_upload = FileField(
        "About — main image (choose file)",
        description="JPG, PNG, WebP or GIF. Saved under /uploads/gallery/… when uploaded.",
    )
    about_secondary_upload = FileField(
        "About — secondary image (choose file)",
        description="JPG, PNG, WebP or GIF.",
    )
    about_years_badge = StringField(
        "Years badge",
        validators=[Optional(), validators.Length(max=20)],
    )
    menu_preview_upload = FileField(
        "Menu preview (choose file)",
        description="JPG, PNG, WebP or GIF.",
    )
    cta_bg_upload = FileField(
        "CTA section background (choose file)",
        description="JPG, PNG, WebP or GIF.",
    )


class ServiceCategoryForm(Form):
    name = StringField("Name", validators=[DataRequired(), validators.Length(max=120)])
    slug = StringField("Slug", validators=[DataRequired(), validators.Length(max=180)])
    image_upload = FileField(
        "Category image (choose file)",
        description="JPG, PNG, WebP or GIF.",
    )
    description = TextAreaField("Description", validators=[Optional()])
    reference_url = StringField(
        "Source URL",
        validators=[Optional(), validators.Length(max=500)],
        description="Optional public catalog page — Hair/Skin rows sync on API startup.",
    )
    sort_order = IntegerField(
        "Sort order",
        default=0,
        validators=[Optional(), NumberRange(min=0, max=99999)],
    )
    is_active = BooleanField("Active", default=True)


class GalleryImageForm(Form):
    upload = FileField(
        "Image (choose file)",
        description="JPG, PNG, WebP or GIF.",
    )
    caption = StringField("Caption", validators=[Optional(), validators.Length(max=200)])
    sort_order = IntegerField(
        "Sort order",
        default=0,
        validators=[Optional(), NumberRange(min=0, max=99999)],
    )
    is_active = BooleanField("Active", default=True)
