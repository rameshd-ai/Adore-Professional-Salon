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

/** Google Maps embed: use lat/lng from DB when both set, else geocode by address text. */
export function mapEmbedSrc(settings) {
  const lat = (settings?.map_lat || '').trim()
  const lng = (settings?.map_lng || '').trim()
  if (lat && lng) {
    const q = encodeURIComponent(`${lat},${lng}`)
    return `https://www.google.com/maps?q=${q}&z=16&output=embed`
  }
  return `https://www.google.com/maps?q=${encodeURIComponent(displayAddress(settings))}&output=embed`
}
