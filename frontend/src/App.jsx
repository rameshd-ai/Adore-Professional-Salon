import { Routes, Route, Navigate } from 'react-router-dom'
import ScrollToHash from './ScrollToHash'
import Layout from './Layout'
import Home from './pages/Home'
import MenuPage from './pages/MenuPage'
import GalleryPage from './pages/GalleryPage'
import BlogPage from './pages/BlogPage'
import BlogPostPage from './pages/BlogPostPage'
import ContactPage from './pages/ContactPage'

export default function App() {
  return (
    <>
      <ScrollToHash />
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="services" element={<Navigate to="/menu" replace />} />
        <Route path="menu" element={<MenuPage />} />
        <Route path="gallery" element={<GalleryPage />} />
        <Route path="blog" element={<BlogPage />} />
        <Route path="blog/:slug" element={<BlogPostPage />} />
        <Route path="contact" element={<ContactPage />} />
      </Route>
    </Routes>
    </>
  )
}
