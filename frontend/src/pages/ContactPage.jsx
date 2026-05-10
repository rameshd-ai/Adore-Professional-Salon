import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { postContact } from '../api'
import { displayAddress, displayEmail, displayPhone, mapEmbedSrc } from '../defaultBrand'

export default function ContactPage() {
  const { settings } = useOutletContext()
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' })
  const [msg, setMsg] = useState(null)

  async function onSubmit(e) {
    e.preventDefault()
    setMsg(null)
    try {
      await postContact({
        name: form.name,
        email: form.email,
        subject: form.subject,
        message: form.message,
      })
      setMsg({ ok: true, text: 'Message sent. We will get back to you soon.' })
      setForm({ name: '', email: '', subject: '', message: '' })
    } catch (err) {
      setMsg({ ok: false, text: err.message || 'Could not send message.' })
    }
  }

  return (
    <main className="section-padding min-vh-50">
      <div className="container">
        <div className="row justify-content-center text-center mb-5">
          <div className="col-lg-8">
            <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
              Contact
            </span>
            <h1 className="display-5 font-heading fw-bold mb-3">Get in touch</h1>
            <p className="text-secondary mb-0">
              {displayPhone(settings)} · {displayEmail(settings)}
            </p>
          </div>
        </div>
        <div className="row g-5">
          <div className="col-lg-6">
            <div className="ratio ratio-4x3 bg-light mb-3">
              <iframe
                title="Map"
                className="border-0"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                src={mapEmbedSrc(settings)}
              />
            </div>
            <p className="text-secondary mb-0">{displayAddress(settings)}</p>
          </div>
          <div className="col-lg-6">
            <form className="bg-light p-4 p-lg-5" onSubmit={onSubmit}>
              {msg && (
                <div
                  className={`alert ${msg.ok ? 'alert-success' : 'alert-danger'} rounded-0 mb-3`}
                  role="alert"
                >
                  {msg.text}
                </div>
              )}
              <div className="mb-3">
                <label className="form-label small text-uppercase">Name</label>
                <input
                  required
                  className="form-control rounded-0"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div className="mb-3">
                <label className="form-label small text-uppercase">Email</label>
                <input
                  required
                  type="email"
                  className="form-control rounded-0"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                />
              </div>
              <div className="mb-3">
                <label className="form-label small text-uppercase">Subject</label>
                <input
                  className="form-control rounded-0"
                  value={form.subject}
                  onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
                />
              </div>
              <div className="mb-3">
                <label className="form-label small text-uppercase">Message</label>
                <textarea
                  required
                  rows={5}
                  className="form-control rounded-0"
                  value={form.message}
                  onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
                />
              </div>
              <button type="submit" className="btn btn-primary rounded-0 px-5">
                Send
              </button>
            </form>
          </div>
        </div>
      </div>
    </main>
  )
}
