import { useEffect, useState } from 'react'
import { getGallery } from '../api'

export default function GalleryPage() {
  const [images, setImages] = useState([])
  const [err, setErr] = useState(null)

  useEffect(() => {
    getGallery()
      .then(setImages)
      .catch((e) => setErr(String(e.message || e)))
  }, [])

  if (err) {
    return (
      <div className="container py-5">
        <p className="text-danger">{err}</p>
      </div>
    )
  }

  return (
    <main className="section-padding bg-light min-vh-50">
      <div className="container">
        <div className="text-center mb-5">
          <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
            Gallery
          </span>
          <h1 className="display-5 font-heading fw-bold">Our work</h1>
        </div>
        <div className="row g-3">
          {images.map((g) => (
            <div key={g.id} className="col-6 col-md-4 col-lg-3">
              <figure className="mb-0 bg-white shadow-sm">
                <img src={g.image_url} alt={g.caption || ''} className="img-fluid w-100" />
                {g.caption && (
                  <figcaption className="small text-secondary p-2">{g.caption}</figcaption>
                )}
              </figure>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}
