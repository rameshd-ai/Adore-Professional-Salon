const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

async function fetchJson(path, options) {
  const url = `${base}${path}`
  const r = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  })
  if (!r.ok) {
    const text = await r.text()
    throw new Error(text || r.statusText)
  }
  if (r.status === 204) return null
  return r.json()
}

export function getSettings() {
  return fetchJson('/api/settings')
}

export function getHeroSlides() {
  return fetchJson('/api/hero-slides')
}

export function getServices() {
  return fetchJson('/api/services')
}

export function getServiceCategories() {
  return fetchJson('/api/service-categories')
}

export function getMenu() {
  return fetchJson('/api/menu')
}

export function getGallery() {
  return fetchJson('/api/gallery')
}

export function getBlogPosts() {
  return fetchJson('/api/blog')
}

export function getBlogPost(slug) {
  return fetchJson(`/api/blog/${encodeURIComponent(slug)}`)
}

export function getTestimonials() {
  return fetchJson('/api/testimonials')
}

export function postBooking(body) {
  return fetchJson('/api/bookings', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function postContact(body) {
  return fetchJson('/api/contact', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
