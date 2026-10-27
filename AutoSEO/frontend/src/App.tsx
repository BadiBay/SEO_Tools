import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { api } from './api/client'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import AnalysisPage from './pages/AnalysisPage'
import PaidLinksPage from './pages/PaidLinksPage'
import PaidLinkDetailPage from './pages/PaidLinkDetailPage'
import FreeLinksPage from './pages/FreeLinksPage'
import FreeLinkDetailPage from './pages/FreeLinkDetailPage'
import AltTagsPage from './pages/AltTagsPage'
import AltTagBatchPage from './pages/AltTagBatchPage'
import NotificationsPage from './pages/NotificationsPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    // Initial fetch
    fetchUnreadCount()
    
    // Polling every 30 seconds
    const interval = setInterval(fetchUnreadCount, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchUnreadCount = async () => {
    try {
      const data = await api.getNotifications({ unread_only: true })
      setUnreadCount(data.length)
    } catch (e) {
      console.error("Failed to fetch notifications count", e)
    }
  }

  return (
    <BrowserRouter>
      <div className="app-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <div className="sidebar-logo">
              <div className="logo-icon">AS</div>
              <span className="logo-text">AutoSEO</span>
            </div>
          </div>
          <nav className="sidebar-nav">
            <div className="nav-section-title">Основное</div>
            <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
              <span className="nav-icon">📊</span>
              Проекты
            </NavLink>

            <div className="nav-section-title">Модули</div>
            <NavLink to="/competitors" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="nav-icon">🔍</span>
              Анализ конкурентов
            </NavLink>
            <NavLink to="/free-links" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="nav-icon">🔗</span>
              Бесплатные ссылки
            </NavLink>
            <NavLink to="/paid-links" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="nav-icon">💰</span>
              Платные ссылки
            </NavLink>
            <NavLink to="/alt-tags" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="nav-icon">🖼️</span>
              Alt-теги
            </NavLink>

            <div className="nav-section-title">Система</div>
            <NavLink to="/notifications" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span className="nav-icon">🔔</span>
                Уведомления
              </div>
              {unreadCount > 0 && (
                <span style={{ background: 'var(--danger)', color: 'white', borderRadius: 10, padding: '2px 6px', fontSize: 12, fontWeight: 'bold' }}>
                  {unreadCount}
                </span>
              )}
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="nav-icon">⚙️</span>
              Настройки
            </NavLink>
          </nav>
        </aside>

        {/* Main */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ProjectsPage />} />
            <Route path="/project/:id" element={<ProjectDetailPage />} />
            <Route path="/project/:id/paid-links" element={<PaidLinksPage />} />
            <Route path="/project/:id/paid-links/:linkId" element={<PaidLinkDetailPage />} />
            <Route path="/project/:id/free-links" element={<FreeLinksPage />} />
            <Route path="/project/:id/free-links/:linkId" element={<FreeLinkDetailPage />} />
            <Route path="/project/:id/alt-tags" element={<AltTagsPage />} />
            <Route path="/project/:id/alt-tags/:batchId" element={<AltTagBatchPage />} />
            <Route path="/competitors" element={<AnalysisPage />} />
            <Route path="/paid-links" element={<PaidLinksPage />} />
            <Route path="/free-links" element={<FreeLinksPage />} />
            <Route path="/alt-tags" element={<AltTagsPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
