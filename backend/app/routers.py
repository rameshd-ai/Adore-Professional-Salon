from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    BlogPost,
    BookingInquiry,
    ContactMessage,
    GalleryImage,
    HeroSlide,
    Service,
    ServiceCategory,
    SiteSettings,
    Testimonial,
)
from app.schemas import (
    BlogPostDetailOut,
    BlogPostListOut,
    BookingCreate,
    ContactCreate,
    GalleryImageOut,
    HeroSlideOut,
    MenuItemOut,
    ServiceCategoryOut,
    ServiceOut,
    SiteSettingsOut,
    TestimonialOut,
)


def _service_out(s: Service) -> ServiceOut:
    cat_name = s.service_category.name if s.service_category else "General"
    return ServiceOut(
        id=s.id,
        category_id=s.category_id,
        category=cat_name,
        title=s.title,
        slug=s.slug,
        short_description=s.short_description,
        image_url=s.image_url,
        price_from=s.price_from,
        sort_order=s.sort_order,
    )

api_router = APIRouter()


@api_router.get("/settings", response_model=SiteSettingsOut)
def read_settings(db: Session = Depends(get_db)) -> SiteSettings:
    row = db.query(SiteSettings).filter(SiteSettings.id == 1).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Settings not found")
    return row


@api_router.get("/hero-slides", response_model=list[HeroSlideOut])
def list_hero_slides(db: Session = Depends(get_db)) -> list[HeroSlide]:
    return (
        db.query(HeroSlide)
        .filter(HeroSlide.is_active.is_(True))
        .order_by(HeroSlide.sort_order, HeroSlide.id)
        .all()
    )


@api_router.get("/service-categories", response_model=list[ServiceCategoryOut])
def list_service_categories(db: Session = Depends(get_db)) -> list[ServiceCategory]:
    return (
        db.query(ServiceCategory)
        .filter(ServiceCategory.is_active.is_(True))
        .order_by(ServiceCategory.sort_order, ServiceCategory.id)
        .all()
    )


@api_router.get("/services", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)) -> list[ServiceOut]:
    rows = (
        db.query(Service)
        .options(joinedload(Service.service_category))
        .filter(Service.is_active.is_(True))
        .order_by(Service.sort_order, Service.id)
        .all()
    )
    return [_service_out(s) for s in rows]


@api_router.get("/menu", response_model=list[MenuItemOut])
def list_menu(db: Session = Depends(get_db)) -> list[MenuItemOut]:
    rows = (
        db.query(Service)
        .join(ServiceCategory, Service.category_id == ServiceCategory.id)
        .options(joinedload(Service.service_category))
        .filter(Service.is_active.is_(True))
        .order_by(
            ServiceCategory.sort_order,
            ServiceCategory.name,
            Service.sort_order,
            Service.id,
        )
        .all()
    )
    return [
        MenuItemOut(
            id=s.id,
            category=s.service_category.name if s.service_category else "General",
            name=s.title,
            description=s.short_description or "",
            price=s.price_from or "",
            sort_order=s.sort_order,
        )
        for s in rows
    ]


@api_router.get("/gallery", response_model=list[GalleryImageOut])
def list_gallery(db: Session = Depends(get_db)) -> list[GalleryImage]:
    return (
        db.query(GalleryImage)
        .filter(GalleryImage.is_active.is_(True))
        .order_by(GalleryImage.sort_order, GalleryImage.id)
        .all()
    )


@api_router.get("/blog", response_model=list[BlogPostListOut])
def list_blog(db: Session = Depends(get_db)) -> list[BlogPost]:
    return (
        db.query(BlogPost)
        .filter(BlogPost.is_published.is_(True))
        .order_by(BlogPost.published_at.desc(), BlogPost.id)
        .all()
    )


@api_router.get("/blog/{slug}", response_model=BlogPostDetailOut)
def get_blog_post(slug: str, db: Session = Depends(get_db)) -> BlogPost:
    post = (
        db.query(BlogPost)
        .filter(BlogPost.slug == slug, BlogPost.is_published.is_(True))
        .first()
    )
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


@api_router.get("/testimonials", response_model=list[TestimonialOut])
def list_testimonials(db: Session = Depends(get_db)) -> list[Testimonial]:
    return (
        db.query(Testimonial)
        .filter(Testimonial.is_active.is_(True))
        .order_by(Testimonial.sort_order, Testimonial.id)
        .all()
    )


@api_router.post("/bookings", status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> dict:
    row = BookingInquiry(
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        service=(payload.service or "").strip(),
        preferred_date=payload.preferred_date,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "ok": True}


@api_router.post("/contact", status_code=status.HTTP_201_CREATED)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)) -> dict:
    row = ContactMessage(
        name=payload.name.strip(),
        email=str(payload.email).strip(),
        subject=(payload.subject or "").strip(),
        message=payload.message.strip(),
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "ok": True}
