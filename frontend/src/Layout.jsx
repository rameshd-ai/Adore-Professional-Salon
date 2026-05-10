import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { getSettings } from './api'
import {
  DEFAULT_MAP_LAT,
  DEFAULT_MAP_LNG,
  DEFAULT_SALON_NAME,
  displayAddress,
  displayEmail,
  displayHoursLine,
  displayPhone,
} from './defaultBrand'
import SmartLink from './SmartLink'

/** When the API is down, still render the shell so navigation and pages work. */
const FALLBACK_SETTINGS = {
  salon_name: DEFAULT_SALON_NAME,
  logo_url: '',
  phone: displayPhone({}),
  email: displayEmail({}),
  hours_line: displayHoursLine({}),
  address: displayAddress({}),
  map_lat: DEFAULT_MAP_LAT,
  map_lng: DEFAULT_MAP_LNG,
  discount_banner_html: '',
  discount_book_link_label: 'Book Now',
  facebook_url: '',
  instagram_url: '',
  twitter_url: '',
  footer_tagline: 'A premium hair salon dedicated to exceptional service and style.',
  about_subtitle: 'Beauty, skin & hair under one roof',
  about_heading: 'Care that shows — from facials to finishing touches',
  about_para1: `${DEFAULT_SALON_NAME} brings together experienced stylists and skin therapists in a calm, hygienic space. Start the API (port 8001) to load your live site settings from the database.`,
  about_para2:
    'We use trusted professional products, clear pricing, and unhurried appointments so you always leave feeling confident — never rushed.',
  about_main_image: '/site-media/about-main.jpg',
  about_secondary_image: '/site-media/about-secondary.jpg',
  about_years_badge: '10+',
  menu_preview_image: '/site-media/about-secondary.jpg',
  cta_bg_image: '/site-media/cta-bg.jpg',
}

function dismissNavbarOffcanvas() {
  if (typeof window === 'undefined' || !window.bootstrap?.Offcanvas) return
  const el = document.getElementById('offcanvasNavbar')
  const inst = el && window.bootstrap.Offcanvas.getInstance(el)
  inst?.hide()
}

export default function Layout() {
  const [settings, setSettings] = useState(null)
  const [bannerOpen, setBannerOpen] = useState(true)
  const [err, setErr] = useState(null)

  useEffect(() => {
    getSettings()
      .then((data) => {
        setErr(null)
        setSettings(data)
      })
      .catch((e) => {
        setErr(String(e.message || e))
        setSettings(FALLBACK_SETTINGS)
      })
  }, [])

  useEffect(() => {
    if (!settings) return
    const name = (settings.salon_name || '').trim() || DEFAULT_SALON_NAME
    document.title = `${name} – Salon`

    let link = document.querySelector("link[rel='icon']")
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    const logo = (settings.logo_url || '').trim()
    if (logo) {
      link.href = logo
      const lower = logo.split('?')[0].toLowerCase()
      if (lower.endsWith('.svg')) link.type = 'image/svg+xml'
      else if (lower.endsWith('.png')) link.type = 'image/png'
      else if (lower.endsWith('.webp')) link.type = 'image/webp'
      else if (lower.endsWith('.gif')) link.type = 'image/gif'
      else if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) link.type = 'image/jpeg'
      else link.removeAttribute('type')
    } else {
      link.href = '/favicon.svg'
      link.type = 'image/svg+xml'
    }
  }, [settings])

  if (!settings) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '40vh' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading…</span>
        </div>
      </div>
    )
  }

  const brand = (settings.salon_name || '').trim() || DEFAULT_SALON_NAME

  return (
    <>
      {err && (
        <div className="alert alert-warning text-center rounded-0 border-0 mb-0 py-2 small" role="alert">
          Could not reach the API (<code>/api/settings</code>). Showing placeholder content — start the
          backend (<strong>127.0.0.1:8001</strong> after <code>npm run build</code> in <code>frontend/</code>)
          or set <code>VITE_API_URL</code>.{' '}
          <span className="text-muted">{err}</span>
        </div>
      )}
      {bannerOpen && settings.discount_banner_html && (
        <div
          className="discount-banner py-2 text-center alert-dismissible fade show mb-0"
          role="alert"
        >
          <div className="container">
            <span
              className="me-2"
              dangerouslySetInnerHTML={{ __html: settings.discount_banner_html }}
            />
            <SmartLink href="/contact" className="fw-bold">
              {settings.discount_book_link_label || 'Book Now'}
            </SmartLink>
            <button
              type="button"
              className="btn-close shadow-none top-50 translate-middle-y me-3"
              aria-label="Close"
              onClick={() => setBannerOpen(false)}
            />
          </div>
        </div>
      )}

      <div className="top-bar d-none d-lg-block">
        <div className="container">
          <div className="d-flex justify-content-between align-items-center">
            <div className="top-info d-flex gap-4">
              <a href={`tel:${displayPhone(settings)}`}>
                <i className="bi bi-telephone me-2" /> {displayPhone(settings)}
              </a>
              <a href={`mailto:${displayEmail(settings)}`}>
                <i className="bi bi-envelope me-2" /> {displayEmail(settings)}
              </a>
              <span>
                <i className="bi bi-clock me-2" /> {displayHoursLine(settings)}
              </span>
            </div>
            <div className="top-social d-flex gap-3">
              {settings.facebook_url && (
                <a href={settings.facebook_url} target="_blank" rel="noreferrer">
                  <i className="bi bi-facebook" />
                </a>
              )}
              {settings.instagram_url && (
                <a href={settings.instagram_url} target="_blank" rel="noreferrer">
                  <i className="bi bi-instagram" />
                </a>
              )}
              {settings.twitter_url && (
                <a href={settings.twitter_url} target="_blank" rel="noreferrer">
                  <i className="bi bi-twitter-x" />
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      <header className="main-header sticky-top">
        <nav className="navbar navbar-expand-lg">
          <div className="container">
            <NavLink className="navbar-brand d-flex align-items-center gap-2" to="/">
              {settings.logo_url?.trim() ? (
                <img
                  src={settings.logo_url.trim()}
                  alt=""
                  className="brand-logo"
                  style={{ maxHeight: 36, width: 'auto' }}
                />
              ) : null}
              <span>
                {brand}
                <span className="text-primary">.</span>
              </span>
            </NavLink>

            <button
              className="navbar-toggler border-0 d-lg-none"
              type="button"
              data-bs-toggle="offcanvas"
              data-bs-target="#offcanvasNavbar"
              aria-controls="offcanvasNavbar"
            >
              <span className="navbar-toggler-icon" />
            </button>

            <div
              className="offcanvas offcanvas-end offcanvas-lg"
              tabIndex={-1}
              id="offcanvasNavbar"
              aria-labelledby="offcanvasNavbarLabel"
            >
              <div className="offcanvas-header d-lg-none border-bottom">
                <h5 className="offcanvas-title font-heading" id="offcanvasNavbarLabel">
                  {brand}.
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  data-bs-dismiss="offcanvas"
                  aria-label="Close"
                />
              </div>
              <div className="offcanvas-body p-lg-0">
                <ul className="navbar-nav ms-auto align-items-lg-center gap-lg-4">
                  <li className="nav-item">
                    <NavLink className="nav-link" to="/" end onClick={dismissNavbarOffcanvas}>
                      Home
                    </NavLink>
                  </li>
                  <li className="nav-item">
                    <NavLink className="nav-link" to="/#about" onClick={dismissNavbarOffcanvas}>
                      About
                    </NavLink>
                  </li>
                  <li className="nav-item">
                    <NavLink className="nav-link" to="/menu" onClick={dismissNavbarOffcanvas}>
                      Menu
                    </NavLink>
                  </li>
                  <li className="nav-item">
                    <NavLink className="nav-link" to="/gallery" onClick={dismissNavbarOffcanvas}>
                      Gallery
                    </NavLink>
                  </li>
                  <li className="nav-item">
                    <NavLink className="nav-link" to="/blog" onClick={dismissNavbarOffcanvas}>
                      Blog
                    </NavLink>
                  </li>
                  <li className="nav-item">
                    <NavLink className="nav-link" to="/contact" onClick={dismissNavbarOffcanvas}>
                      Contact
                    </NavLink>
                  </li>
                  <li className="nav-item ms-lg-3">
                    <NavLink
                      to="/contact"
                      className="btn btn-primary btn-book rounded-0 px-4 py-2"
                      onClick={dismissNavbarOffcanvas}
                    >
                      Book Now
                    </NavLink>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </nav>
      </header>

      <Outlet context={{ settings }} />

      <footer className="site-footer bg-dark text-white pt-5">
        <div className="container pb-5">
          <div className="row g-5">
            <div className="col-lg-4">
              <NavLink className="d-block mb-4 text-decoration-none" to="/">
                <h2 className="text-white font-heading fw-bold">
                  {brand}
                  <span className="text-primary">.</span>
                </h2>
              </NavLink>
              <p className="text-white-50 mb-4">{settings.footer_tagline}</p>
              <div className="social-links d-flex gap-3">
                {settings.facebook_url && (
                  <a
                    href={settings.facebook_url}
                    className="text-white bg-white bg-opacity-10 rounded-circle d-flex align-items-center justify-content-center"
                    style={{ width: 40, height: 40 }}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <i className="bi bi-facebook" />
                  </a>
                )}
                {settings.instagram_url && (
                  <a
                    href={settings.instagram_url}
                    className="text-white bg-white bg-opacity-10 rounded-circle d-flex align-items-center justify-content-center"
                    style={{ width: 40, height: 40 }}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <i className="bi bi-instagram" />
                  </a>
                )}
                {settings.twitter_url && (
                  <a
                    href={settings.twitter_url}
                    className="text-white bg-white bg-opacity-10 rounded-circle d-flex align-items-center justify-content-center"
                    style={{ width: 40, height: 40 }}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <i className="bi bi-twitter-x" />
                  </a>
                )}
              </div>
            </div>
            <div className="col-lg-4">
              <h4 className="h5 font-heading fw-bold mb-4">Contact Info</h4>
              <ul className="list-unstyled text-white-50">
                <li className="mb-3 d-flex align-items-start">
                  <i className="bi bi-geo-alt text-primary me-3 flex-shrink-0 mt-1" aria-hidden />
                  <span className="flex-grow-1 text-break">{displayAddress(settings)}</span>
                </li>
                <li className="mb-3 d-flex">
                  <i className="bi bi-telephone text-primary me-3" />
                  <a href={`tel:${displayPhone(settings)}`} className="text-white-50 text-decoration-none">
                    {displayPhone(settings)}
                  </a>
                </li>
                <li className="mb-3 d-flex">
                  <i className="bi bi-envelope text-primary me-3" />
                  <a
                    href={`mailto:${displayEmail(settings)}`}
                    className="text-white-50 text-decoration-none"
                  >
                    {displayEmail(settings)}
                  </a>
                </li>
              </ul>
            </div>
            <div className="col-lg-4">
              <h4 className="h5 font-heading fw-bold mb-4">Hours</h4>
              <p className="text-white-50 mb-0">{displayHoursLine(settings)}</p>
            </div>
          </div>
        </div>
        <div className="footer-bottom border-top border-secondary border-opacity-25 py-4">
          <div className="container text-center">
            <p className="mb-0 text-white-50 fs-7">
              &copy; {new Date().getFullYear()} {brand}. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </>
  )
}
