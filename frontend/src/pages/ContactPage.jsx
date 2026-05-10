import { useOutletContext } from 'react-router-dom'
import {
  displayAddress,
  displayEmail,
  displayHoursLine,
  displayPhone,
  mapEmbedSrc,
  phoneTelHref,
} from '../defaultBrand'

export default function ContactPage() {
  const { settings } = useOutletContext()

  return (
    <main className="contact-page min-vh-50">
      <div className="container section-padding pb-4">
        <div className="row justify-content-center text-center">
          <div className="col-lg-8">
            <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
              Contact
            </span>
            <h1 className="display-5 font-heading fw-bold mb-3">Get in touch</h1>
            <p className="text-secondary mb-4 mb-lg-5">
              Call us to book or ask a question — we&apos;re happy to help.
            </p>
          </div>
        </div>
      </div>

      <section className="contact-page-map-full bg-light" aria-label="Salon location map">
        <iframe
          title="Map"
          className="contact-page-map-iframe border-0"
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          src={mapEmbedSrc(settings)}
        />
      </section>

      <div className="container section-padding pt-4 pt-lg-5 pb-5">
        <div className="row justify-content-center text-center">
          <div className="col-lg-8">
            <p className="text-secondary mb-4">{displayAddress(settings)}</p>
            <a
              href={phoneTelHref(settings)}
              className="btn btn-primary btn-lg rounded-0 px-5 py-3 text-uppercase letter-spacing-1 fw-medium"
            >
              <i className="bi bi-telephone me-2" aria-hidden />
              Call {displayPhone(settings)}
            </a>
            <p className="text-secondary mt-4 mb-2">{displayHoursLine(settings)}</p>
            <p className="mb-0">
              <a href={`mailto:${displayEmail(settings)}`} className="text-primary text-decoration-none">
                {displayEmail(settings)}
              </a>
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
