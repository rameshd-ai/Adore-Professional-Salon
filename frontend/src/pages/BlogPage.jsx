import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getBlogPosts } from '../api'

export default function BlogPage() {
  const [posts, setPosts] = useState([])
  const [err, setErr] = useState(null)

  useEffect(() => {
    getBlogPosts()
      .then(setPosts)
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
    <main className="section-padding min-vh-50">
      <div className="container">
        <div className="text-center mb-5">
          <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
            Blog
          </span>
          <h1 className="display-5 font-heading fw-bold">Tips &amp; news</h1>
        </div>
        <div className="row g-4">
          {posts.map((p) => (
            <div key={p.id} className="col-md-6 col-lg-4">
              <article className="bg-light h-100 shadow-sm">
                <Link to={`/blog/${p.slug}`} className="text-decoration-none text-dark">
                  <img
                    src={p.image_url}
                    alt=""
                    className="img-fluid w-100"
                    style={{ height: 220, objectFit: 'cover' }}
                  />
                  <div className="p-4">
                    <p className="text-secondary small mb-1">
                      {p.category} · {new Date(p.published_at).toLocaleDateString()}
                    </p>
                    <h2 className="h4 font-heading fw-bold">{p.title}</h2>
                    <p className="text-secondary mb-0">{p.excerpt}</p>
                  </div>
                </Link>
              </article>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}
