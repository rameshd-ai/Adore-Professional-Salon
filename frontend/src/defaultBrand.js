/**
 * Fallback when `/api/settings` is unavailable. The live site always uses
 * `phone`, `email`, `hours_line`, and `address` from the database (Site settings).
 * Keep these aligned with `backend/app/brand_defaults.py`.
 */
export const DEFAULT_SALON_NAME = 'Adore Professional Salon'
export const DEFAULT_PHONE = '+91 98765 43210'
export const DEFAULT_EMAIL = 'hello@adoreprofessionalsalon.com'
export const DEFAULT_HOURS_LINE = 'Mon – Sat: 9AM – 8PM'
export const DEFAULT_ADDRESS =
  'VIP Road, Police Line, Sri Vijaya Puram, 744103, Andaman and Nicobar Islands, India'
export const DEFAULT_MAP_LAT = '11.659874'
export const DEFAULT_MAP_LNG = '92.736025'

/** Prefer DB `site_settings`; use defaults only when a field is blank (e.g. API offline). */
export function displayPhone(settings) {
  return (settings?.phone || '').trim() || DEFAULT_PHONE
}

/** `tel:` href — strips spaces; keeps leading `+` for international numbers. */
export function phoneTelHref(settings) {
  const display = displayPhone(settings)
  const cleaned = display.replace(/[^\d+]/g, '')
  return cleaned ? `tel:${cleaned}` : `tel:${DEFAULT_PHONE.replace(/[^\d+]/g, '')}`
}

export function displayEmail(settings) {
  return (settings?.email || '').trim() || DEFAULT_EMAIL
}

export function displayHoursLine(settings) {
  return (settings?.hours_line || '').trim() || DEFAULT_HOURS_LINE
}

export function displayAddress(settings) {
  return (settings?.address || '').trim() || DEFAULT_ADDRESS
}

/** Maps Embed API key from Vite (build-time). Restrict key by HTTP referrer in Google Cloud. */
function googleMapsEmbedKey() {
  const k = import.meta.env.VITE_GOOGLE_MAPS_EMBED_KEY
  return typeof k === 'string' ? k.trim() : ''
}

/**
 * Google Maps iframe for Contact page.
 * If ``VITE_GOOGLE_MAPS_EMBED_KEY`` is set at build time, uses Embed API (fewer iframe errors).
 * Otherwise falls back to a plain embed URL.
 */
export function mapEmbedSrc(settings) {
  const lat = (settings?.map_lat || '').trim()
  const lng = (settings?.map_lng || '').trim()
  const key = googleMapsEmbedKey()

  if (key) {
    const base = 'https://www.google.com/maps/embed/v1/place'
    const k = encodeURIComponent(key)
    if (lat && lng) {
      const q = encodeURIComponent(`${lat},${lng}`)
      return `${base}?key=${k}&q=${q}&zoom=16`
    }
    const q = encodeURIComponent(displayAddress(settings))
    return `${base}?key=${k}&q=${q}&zoom=16`
  }

  const tail = '&z=16&hl=en&output=embed&iwloc=near'
  const fallback = 'https://maps.google.com/maps'
  if (lat && lng) {
    const q = encodeURIComponent(`${lat},${lng}`)
    return `${fallback}?q=${q}${tail}`
  }
  return `${fallback}?q=${encodeURIComponent(displayAddress(settings))}${tail}`
}
