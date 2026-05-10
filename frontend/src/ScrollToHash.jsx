import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Scroll to #id when the route hash changes (e.g. /#/about or /menu#cat-hair). */
export default function ScrollToHash() {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (!hash || hash.length < 2) return
    const id = decodeURIComponent(hash.slice(1))
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [pathname, hash])

  return null
}
