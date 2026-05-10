import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getServiceCategories, getServices } from '../api'
import { categoryAnchorId, groupServicesByCategory, placeholderServiceImage } from '../serviceCategories'

const ALL = '__all__'

function categoryImageUrl(categoryName, items, catByName) {
  const meta = catByName.get(categoryName)
  if (meta?.image_url?.trim()) return meta.image_url.trim()
  const fromSvc = items.find((s) => s.image_url?.trim())?.image_url
  if (fromSvc?.trim()) return fromSvc.trim()
  return placeholderServiceImage()
}

function MenuCategoryBlock({ category, items, showCategoryHeading, catByName }) {
  const anchor = categoryAnchorId(category)
  const img = categoryImageUrl(category, items, catByName)
  const last = items.length - 1

  return (
    <section id={anchor} className="mb-5 pb-2 scroll-margin-top">
      {showCategoryHeading ? (
        <div className="menu-category text-center mb-4">
          <h2 className="font-heading fw-bold fs-2 mb-0">{category}</h2>
          <div
            className="separator mx-auto bg-primary mt-3 mb-0"
            style={{ width: 60, height: 2 }}
          />
        </div>
      ) : null}

      <div className="row g-4 g-lg-5 align-items-start">
        <div className="col-lg-5">
          <img
            src={img}
            alt=""
            className="img-fluid w-100 shadow-sm"
            style={{ minHeight: 260, maxHeight: 440, objectFit: 'cover' }}
            loading="lazy"
          />
        </div>
        <div className="col-lg-7">
          <div className="menu-list bg-white p-4 p-md-5 shadow-sm">
            {items.map((svc, i) => (
              <div
                key={svc.id}
                className={`price-item ${i === last ? 'mb-0 pb-0' : 'mb-4 pb-3 border-bottom border-light'}`}
              >
                <div className="w-100">
                  <h5 className="font-heading fw-bold mb-1 d-flex flex-wrap justify-content-between gap-2 align-items-baseline">
                    <span>{svc.title}</span>
                    <span className="text-primary text-nowrap">{svc.price_from}</span>
                  </h5>
                  {svc.short_description?.trim() ? (
                    <p className="text-secondary fs-7 fst-italic mb-0">{svc.short_description}</p>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default function MenuPage() {
  const [services, setServices] = useState([])
  const [categories, setCategories] = useState([])
  const [err, setErr] = useState(null)
  const [activeTab, setActiveTab] = useState(ALL)
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([getServices(), getServiceCategories()])
      .then(([svc, cats]) => {
        setServices(svc)
        setCategories(cats)
      })
      .catch((e) => setErr(String(e.message || e)))
  }, [])

  const grouped = useMemo(() => groupServicesByCategory(services), [services])

  const catByName = useMemo(() => {
    const m = new Map()
    for (const c of categories) {
      if (c?.name) m.set(c.name, c)
    }
    return m
  }, [categories])

  useEffect(() => {
    const raw = (location.hash || '').replace(/^#/, '')
    if (!raw || !raw.startsWith('cat-')) return
    for (const [cat] of grouped) {
      if (categoryAnchorId(cat) === raw) {
        setActiveTab(cat)
        return
      }
    }
  }, [location.hash, grouped])

  const selectTab = (key) => {
    setActiveTab(key)
    if (key === ALL) {
      navigate({ pathname: '/menu', hash: '' }, { replace: true })
    } else {
      navigate({ pathname: '/menu', hash: `#${categoryAnchorId(key)}` }, { replace: true })
    }
  }

  const filteredGrouped = useMemo(() => {
    if (activeTab === ALL) return grouped
    return grouped.filter(([c]) => c === activeTab)
  }, [grouped, activeTab])

  const showCategoryHeading = activeTab === ALL

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
        <div className="row mb-4">
          <div className="col-lg-10">
            <span className="sub-title text-primary text-uppercase letter-spacing-2 fw-medium mb-2 d-block">
              Menu
            </span>
            <h1 className="display-5 font-heading fw-bold mb-2">Treatments &amp; prices</h1>
            <p className="text-secondary mb-0">
              Browse by category — each row lists the service, details, and price. Book via Contact when you
              are ready.
            </p>
          </div>
        </div>

        <div
          className="menu-category-tabs d-flex flex-wrap gap-2 mb-4 pb-2 border-bottom border-light-subtle"
          role="tablist"
          aria-label="Filter by category"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === ALL}
            className={`btn rounded-0 px-3 py-2 text-uppercase fs-7 letter-spacing-1 fw-medium ${
              activeTab === ALL ? 'btn-primary' : 'btn-outline-dark'
            }`}
            onClick={() => selectTab(ALL)}
          >
            All
          </button>
          {grouped.map(([cat]) => (
            <button
              key={cat}
              type="button"
              role="tab"
              aria-selected={activeTab === cat}
              className={`btn rounded-0 px-3 py-2 text-uppercase fs-7 letter-spacing-1 fw-medium ${
                activeTab === cat ? 'btn-primary' : 'btn-outline-dark'
              }`}
              onClick={() => selectTab(cat)}
            >
              {cat}
            </button>
          ))}
        </div>

        {filteredGrouped.map(([category, items]) =>
          items.length ? (
            <MenuCategoryBlock
              key={category}
              category={category}
              items={items}
              showCategoryHeading={showCategoryHeading}
              catByName={catByName}
            />
          ) : null,
        )}
      </div>
    </main>
  )
}
