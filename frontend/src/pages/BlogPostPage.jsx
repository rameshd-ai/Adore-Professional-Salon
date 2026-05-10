import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getBlogPost } from '../api'

export default function BlogPostPage() {
  const { slug } = useParams()
  const [post, setPost] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!slug) return
    setErr(null)
    getBlogPost(slug)
      .then(setPost)
      .catch(() => setErr('Post not found'))
  }, [slug])

  if (err) {
    return (
      <div className="container py-5 text-center">
        <p className="text-danger mb-3">{err}</p>
        <Link to="/blog">← Back to blog</Link>
      </div>
    )
  }

  if (!post) {
    return (
      <div className="d-flex justify-content-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading…</span>
        </div>
      </div>
    )
  }

  return (
    <main className="section-padding min-vh-50">
      <article className="container" style={{ maxWidth: 800 }}>
        <Link to="/blog" className="text-decoration-none text-secondary small mb-4 d-inline-block">
          ← All posts
        </Link>
        <p className="text-secondary small mb-2">
          {post.category} · {new Date(post.published_at).toLocaleDateString()} · {post.author_name}
        </p>
        <h1 className="display-5 font-heading fw-bold mb-4">{post.title}</h1>
        <img src={post.image_url} alt="" className="img-fluid w-100 mb-4" />
        <div className="blog-body text-secondary" dangerouslySetInnerHTML={{ __html: post.body }} />
      </article>
    </main>
  )
}
