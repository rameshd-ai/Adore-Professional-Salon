/** Group API services by `category` for Essence-style category grids. */

export function categoryAnchorId(category) {
  return (
    'cat-' +
    String(category || 'general')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
  )
}

/**
 * @param {Array<{ category?: string, sort_order?: number }>} services
 * @returns {Array<[string, typeof services]>}
 */
export function groupServicesByCategory(services) {
  const map = new Map()
  for (const s of services) {
    const cat = String(s.category || 'General').trim() || 'General'
    if (!map.has(cat)) map.set(cat, [])
    map.get(cat).push(s)
  }
  for (const arr of map.values()) {
    arr.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
  }
  return [...map.entries()].sort(
    (a, b) => (a[1][0]?.sort_order ?? 0) - (b[1][0]?.sort_order ?? 0),
  )
}

export function placeholderServiceImage() {
  return '/site-media/placeholder-card.svg'
}
