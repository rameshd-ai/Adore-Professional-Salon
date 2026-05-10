import { useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import {
  getBlogPosts,
  getGallery,
  getHeroSlides,
  getServiceCategories,
  getServices,
  getTestimonials,
  postBooking,
} from '../api'
import SmartLink from '../SmartLink'
import { DEFAULT_SALON_NAME } from '../defaultBrand'
import { categoryAnchorId, groupServicesByCategory, placeholderServiceImage } from '../serviceCategories'

function useBootstrapCarousel(id, count) {
  useEffect(() => {
    if (!count || typeof window === 'undefined' || !window.bootstrap) return
    const el = document.getElementById(id)
    if (!el) return
    const existing = window.bootstrap.Carousel.getInstance(el)
    if (existing) existing.dispose()
    const c = new window.bootstrap.Carousel(el, { interval: 5000, ride: 'carousel' })
    return () => c.dispose()
  }, [id, count])
}

export default function Home() {
  const { settings } = useOutletContext()
  const [slides, setSlides] = useState([])
  const [services, setServices] = useState([])
  const [serviceCategories, setServiceCategories] = useState([])
  const [gallery, setGallery] = useState([])
  const [posts, setPosts] = useState([])
  const [testimonials, setTestimonials] = useState([])
  const [booking, setBooking] = useState({
    name: '',
    phone: '',
    service: '',
    preferred_date: '',
  })
  const [bookingMsg, setBookingMsg] = useState(null)

  useEffect(() => {
    Promise.all([
      getHeroSlides().then(setSlides),
      getServices().then(setServices),
      getServiceCategories().then(setServiceCategories),
      getGallery().then(setGallery),
      getBlogPosts().then(setPosts),
      getTestimonials().then(setTestimonials),
    ]).catch(() => {})
  }, [])

  useBootstrapCarousel('heroCarousel', slides.length)
  useBootstrapCarousel('testimonialCarousel', testimonials.length)

  async function onBookingSubmit(e) {
    e.preventDefault()
    setBookingMsg(null)
    try {
      await postBooking({
        name: booking.name,
        phone: booking.phone,
        service: booking.service,
        preferred_date: booking.preferred_date || null,
      })
      setBookingMsg({ ok: true, text: 'Thanks — we will contact you shortly.' })
      setBooking({ name: '', phone: '', service: '', preferred_date: '' })
    } catch (err) {
      setBookingMsg({ ok: false, text: err.message || 'Could not send booking.' })
    }
  }

  const groupedServices = groupServicesByCategory(services)
  const categoryMetaByName = useMemo(() => {
    const m = new Map()
    for (const c of serviceCategories) {
      if (c?.name) m.set(c.name, c)
    }
    return m
  }, [serviceCategories])
  const galleryPreview = gallery.slice(0, 6)
  const blogPreview = posts.slice(0, 3)

  return (
    <>
      <section id="home" className="hero-slider p-0">
        <div
          id="heroCarousel"
          className="carousel slide carousel-fade"
          data-bs-ride="carousel"
          data-bs-interval="5000"
        >
          <div className="carousel-inner">
            {slides.length === 0 ? (
              <div className="carousel-item active">
                <div
                  className="hero-bg"
                  style={{
                    backgroundImage: "url('/site-media/hero-01.jpg')",
                  }}
                />
                <div className="hero-overlay" />
                <div className="container h-100">
                  <div className="row h-100 align-items-center">
                    <div className="col-lg-8 col-xl-7">
                      <div className="hero-content">
                        <h1 className="display-1 font-heading text-white fw-bold mb-4 lh-1">
                          {(settings.salon_name || '').trim() || DEFAULT_SALON_NAME}
                        </h1>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              slides.map((s, i) => (
                <div key={s.id} className={`carousel-item${i === 0 ? ' active' : ''}`}>
                  <div
                    className="hero-bg"
                    style={{ backgroundImage: `url('${s.background_image}')` }}
                  />
                  <div className="hero-overlay" />
                  <div className="container h-100">
                    <div className="row h-100 align-items-center">
                      <div className="col-lg-8 col-xl-7">
                        <div className="hero-content">
                          <div className="d-flex align-items-center mb-3">
                            <span className="line-before me-3" />
                            <span className="sub-title text-uppercase text-white letter-spacing-2 fw-medium">
                              {s.tagline}
                            </span>
                          </div>
                          <h1 className="display-1 font-heading text-white fw-bold mb-4 lh-1">
                            {s.title_line1}
                            <br />
                            <span className="fst-italic fw-normal">{s.title_line2_italic}</span>
                          </h1>
                          <div className="d-flex flex-wrap align-items-center gap-4 mt-5">
                            {s.primary_button_label && (
                              <SmartLink
                                href={s.primary_button_url?.trim() || '/contact'}
                                className="btn btn-outline-light rounded-pill px-4 py-3 d-flex align-items-center gap-2 group-hover-btn"
                              >
                                <span className="text-uppercase letter-spacing-1 fs-7 fw-medium">
                                  {s.primary_button_label}
                                </span>
                                <i
                                  className="bi bi-arrow-right rounded-circle bg-white text-dark p-1 d-flex align-items-center justify-content-center"
                                  style={{ width: 24, height: 24 }}
                                />
                              </SmartLink>
                            )}
                            {s.show_contact_block && (
                              <div className="client-stack d-flex align-items-center gap-3">
                                <div className="avatars d-flex">
                                  <img
                                    src="/site-media/avatar-women-44.jpg"
                                    alt=""
                                    className="rounded-circle border border-2 border-white"
                                    width="45"
                                    height="45"
                                  />
                                  <img
                                    src="/site-media/avatar-women-68.jpg"
                                    alt=""
                                    className="rounded-circle border border-2 border-white ms-n3"
                                    width="45"
                                    height="45"
                                    style={{ marginLeft: -15 }}
                                  />
                                  <img
                                    src="/site-media/avatar-men-32.jpg"
                                    alt=""
                                    className="rounded-circle border border-2 border-white ms-n3"
                                    width="45"
                                    height="45"
                                    style={{ marginLeft: -15 }}
                                  />
                                  <div
                                    className="rounded-circle bg-primary border border-2 border-white ms-n3 d-flex align-items-center justify-content-center text-white fw-bold fs-7"
                                    style={{ width: 45, height: 45, marginLeft: -15 }}
                                  >
                                    +
                                  </div>
                                </div>
                                <div className="text-white lh-sm">
                                  <span className="d-block fw-bold fs-5">325+ Clients</span>
                                  <span className="text-white-50 fs-7">Every Month</span>
                                </div>
                              </div>
                            )}
                            {s.secondary_button_label && (
                              <SmartLink
                                href={s.secondary_button_url?.trim() || '/contact'}
                                className="btn btn-outline-light rounded-pill px-4 py-3"
                              >
                                {s.secondary_button_label}
                              </SmartLink>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="carousel-nav-custom position-absolute top-50 end-0 translate-middle-y me-4 d-none d-md-flex flex-column gap-2 z-2">
            <button
              className="btn btn-outline-light rounded-circle p-0 d-flex align-items-center justify-content-center"
              type="button"
              data-bs-target="#heroCarousel"
              data-bs-slide="prev"
              style={{ width: 50, height: 50 }}
            >
              <i className="bi bi-arrow-left" />
            </button>
            <button
              className="btn btn-outline-light rounded-circle p-0 d-flex align-items-center justify-content-center"
              type="button"
              data-bs-target="#heroCarousel"
              data-bs-slide="next"
              style={{ width: 50, height: 50 }}
            >
              <i className="bi bi-arrow-right" />
            </button>
          </div>
        </div>
        <a href="#about" className="scroll-down text-white text-decoration-none d-none d-md-block">
          <span className="d-block mb-2 text-uppercase fs-7 letter-spacing-2">Scroll</span>
          <i className="bi bi-arrow-down" />
        </a>
      </section>

      <section id="about" className="section-padding overflow-hidden">
        <div className="container">
          <div className="row align-items-center g-5">
            <div className="col-lg-6 position-relative">
              <div className="about-images">
                <img
                  src={settings.about_main_image}
                  alt="Salon"
                  className="img-fluid w-100 main-img"
                  style={{ aspectRatio: '3/4', objectFit: 'cover' }}
                />
                <div className="secondary-img d-none d-md-block">
                  <img src={settings.about_secondary_image} alt="Stylist" className="img-fluid" />
                </div>
                <div className="exp-badge bg-primary text-white d-flex align-items-center justify-content-center text-center">
                  <div>
                    <span className="d-block display-4 fw-bold font-heading lh-1">
                      {settings.about_years_badge}
                    </span>
                    <span className="d-block fs-7 text-uppercase letter-spacing-1">
                      Years
                      <br />
                      Exp.
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div className="col-lg-6 ps-lg-5">
              <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
                {settings.about_subtitle}
              </span>
              <h2 className="display-5 font-heading fw-bold mb-4">{settings.about_heading}</h2>
              <p className="text-secondary mb-4">{settings.about_para1}</p>
              <p className="text-secondary mb-5">{settings.about_para2}</p>
              <div className="row g-4 mb-5">
                <div className="col-6">
                  <div className="d-flex align-items-start">
                    <i className="bi bi-scissors text-primary fs-2 me-3" />
                    <div>
                      <h5 className="font-heading fw-bold mb-1">Expert Stylists</h5>
                      <p className="fs-7 text-secondary mb-0">Highly trained professionals</p>
                    </div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="d-flex align-items-start">
                    <i className="bi bi-stars text-primary fs-2 me-3" />
                    <div>
                      <h5 className="font-heading fw-bold mb-1">Premium Products</h5>
                      <p className="fs-7 text-secondary mb-0">Only the best for your hair</p>
                    </div>
                  </div>
                </div>
              </div>
              <Link
                to="/menu"
                className="btn btn-outline-dark rounded-0 px-4 py-2 text-uppercase fs-7 letter-spacing-1"
              >
                Discover More
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section id="services" className="section-padding bg-light">
        <div className="container">
          <div className="row justify-content-center text-center mb-5">
            <div className="col-lg-8">
              <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
                Menu
              </span>
              <h2 className="display-5 font-heading fw-bold mb-3">What We Offer</h2>
              <p className="text-secondary mb-0">
                Browse categories — open the full menu for every treatment and price.
              </p>
            </div>
          </div>
          <div className="row g-4">
            {groupedServices.map(([category, items]) => {
              const meta = categoryMetaByName.get(category)
              const img =
                meta?.image_url?.trim() ||
                items.find((s) => s.image_url?.trim())?.image_url?.trim() ||
                placeholderServiceImage()
              const hash = categoryAnchorId(category)
              return (
                <div key={category} className="col-6 col-md-4 col-lg-3">
                  <Link
                    to={{ pathname: '/menu', hash: `#${hash}` }}
                    className="text-decoration-none text-dark d-block h-100"
                  >
                    <div className="bg-white rounded-3 shadow-sm h-100 overflow-hidden transition-hover service-category-tile">
                      <div className="ratio ratio-4x3">
                        <img
                          src={img}
                          alt=""
                          className="object-fit-cover w-100 h-100"
                          loading="lazy"
                        />
                      </div>
                      <div className="p-3 text-center">
                        <h3 className="h6 font-heading fw-bold mb-0">{category}</h3>
                      </div>
                    </div>
                  </Link>
                </div>
              )
            })}
          </div>
          <div className="text-center mt-5">
            <Link to="/menu" className="btn btn-primary rounded-0 px-4">
              View full menu
            </Link>
          </div>
        </div>
      </section>

      <section id="book" className="cta-section position-relative py-5 py-lg-6">
        <div
          className="cta-bg"
          style={{
            backgroundImage: `url('${settings.cta_bg_image}')`,
          }}
        />
        <div className="cta-overlay" style={{ background: 'rgba(0,0,0,0.6)' }} />
        <div className="container position-relative z-1 text-center py-5">
          <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
            Make an Appointment
          </span>
          <h2 className="display-4 font-heading fw-bold text-white mb-4">Ready for a New Look?</h2>
          <p className="text-white-50 mb-5 mx-auto" style={{ maxWidth: 600 }}>
            Book your appointment today and let our expert stylists transform your hair.
          </p>
          <form
            className="booking-form bg-white p-4 p-lg-5 mx-auto rounded-0 shadow"
            style={{ maxWidth: 800 }}
            onSubmit={onBookingSubmit}
          >
            {bookingMsg && (
              <div
                className={`alert ${bookingMsg.ok ? 'alert-success' : 'alert-danger'} rounded-0 mb-3`}
                role="alert"
              >
                {bookingMsg.text}
              </div>
            )}
            <div className="row g-3">
              <div className="col-md-4">
                <input
                  required
                  className="form-control rounded-0 py-3 bg-light border-0"
                  placeholder="Your Name"
                  value={booking.name}
                  onChange={(e) => setBooking((b) => ({ ...b, name: e.target.value }))}
                />
              </div>
              <div className="col-md-4">
                <input
                  required
                  type="tel"
                  className="form-control rounded-0 py-3 bg-light border-0"
                  placeholder="Phone Number"
                  value={booking.phone}
                  onChange={(e) => setBooking((b) => ({ ...b, phone: e.target.value }))}
                />
              </div>
              <div className="col-md-4">
                <select
                  className="form-select rounded-0 py-3 bg-light border-0"
                  value={booking.service}
                  onChange={(e) => setBooking((b) => ({ ...b, service: e.target.value }))}
                >
                  <option value="">Select Service</option>
                  {services.map((s) => (
                    <option key={s.id} value={s.title}>
                      {s.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-md-6">
                <input
                  type="date"
                  className="form-control rounded-0 py-3 bg-light border-0"
                  value={booking.preferred_date}
                  onChange={(e) => setBooking((b) => ({ ...b, preferred_date: e.target.value }))}
                />
              </div>
              <div className="col-md-6">
                <button
                  type="submit"
                  className="btn btn-primary w-100 rounded-0 py-3 text-uppercase letter-spacing-1 fw-medium"
                >
                  Book Now
                </button>
              </div>
            </div>
          </form>
        </div>
      </section>

      <section className="section-padding">
        <div className="container">
          <div className="d-flex justify-content-between align-items-end mb-4">
            <div>
              <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
                Gallery
              </span>
              <h2 className="display-5 font-heading fw-bold mb-0">Recent Work</h2>
            </div>
            <Link to="/gallery" className="btn btn-outline-dark rounded-0 d-none d-md-inline-block">
              View all
            </Link>
          </div>
          <div className="row g-3">
            {galleryPreview.map((g) => (
              <div key={g.id} className="col-6 col-md-4">
                <img src={g.image_url} alt={g.caption || ''} className="img-fluid w-100" />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section-padding bg-light">
        <div className="container">
          <div className="d-flex justify-content-between align-items-end mb-4">
            <div>
              <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
                Blog
              </span>
              <h2 className="display-5 font-heading fw-bold mb-0">Tips &amp; news</h2>
            </div>
            <Link to="/blog" className="btn btn-outline-dark rounded-0 d-none d-md-inline-block">
              All posts
            </Link>
          </div>
          <div className="row g-4">
            {blogPreview.map((p) => (
              <div key={p.id} className="col-md-4">
                <Link to={`/blog/${p.slug}`} className="text-decoration-none text-dark">
                  <div className="bg-white h-100 shadow-sm">
                    <img src={p.image_url} alt="" className="img-fluid w-100" style={{ height: 200, objectFit: 'cover' }} />
                    <div className="p-4">
                      <h3 className="h5 font-heading fw-bold">{p.title}</h3>
                      <p className="text-secondary small mb-0">{p.excerpt}</p>
                    </div>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {testimonials.length > 0 && (
        <section id="testimonials" className="section-padding bg-light">
          <div className="container">
            <div className="text-center mb-5">
              <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
                Testimonials
              </span>
              <h2 className="display-5 font-heading fw-bold">Happy Clients</h2>
            </div>
            <div className="row justify-content-center">
              <div className="col-lg-10">
                <div
                  id="testimonialCarousel"
                  className="carousel slide text-center"
                  data-bs-ride="carousel"
                >
                  <div className="carousel-inner">
                    {testimonials.map((t, i) => (
                      <div key={t.id} className={`carousel-item${i === 0 ? ' active' : ''}`}>
                        <div className="testimonial-content py-4">
                          <div className="mb-4 text-primary fs-3">
                            <i className="bi bi-quote" />
                          </div>
                          <p
                            className="fs-4 font-heading fst-italic mb-4 text-dark"
                            style={{ maxWidth: 700, margin: '0 auto' }}
                          >
                            {t.quote}
                          </p>
                          <h5 className="fw-bold text-uppercase letter-spacing-1 fs-7 mb-0">
                            {t.author_name}
                          </h5>
                          <span className="text-secondary fs-7">{t.subtitle}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <button
                    className="carousel-control-prev"
                    type="button"
                    data-bs-target="#testimonialCarousel"
                    data-bs-slide="prev"
                  >
                    <span
                      className="carousel-control-prev-icon bg-dark rounded-circle p-3"
                      aria-hidden="true"
                    />
                    <span className="visually-hidden">Previous</span>
                  </button>
                  <button
                    className="carousel-control-next"
                    type="button"
                    data-bs-target="#testimonialCarousel"
                    data-bs-slide="next"
                  >
                    <span
                      className="carousel-control-next-icon bg-dark rounded-circle p-3"
                      aria-hidden="true"
                    />
                    <span className="visually-hidden">Next</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}
    </>
  )
}
