import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, Project } from '../api/client'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({ name: '', domain: '', region: '' })
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    loadProjects()
  }, [])

  async function loadProjects() {
    try {
      const data = await api.getProjects()
      setProjects(data.items)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      const project = await api.createProject(formData)
      setProjects([project, ...projects])
      setShowForm(false)
      setFormData({ name: '', domain: '', region: '' })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка создания')
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>📊 Проекты</h1>
        <p className="subtitle">Управление клиентскими проектами</p>
      </div>

      <div className="page-body">
        {error && (
          <div className="card" style={{ borderColor: 'var(--danger)', marginBottom: 'var(--space-lg)' }}>
            <p style={{ color: 'var(--danger)' }}>⚠️ {error}</p>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-lg)' }}>
          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Всего: {projects.length} проектов</span>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? '✕ Отмена' : '＋ Новый проект'}
          </button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
            <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>Создание проекта</h3>
            <form onSubmit={handleCreate}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-md)' }}>
                <div className="form-group">
                  <label className="form-label">Название</label>
                  <input
                    className="form-input"
                    placeholder="Окна Москва"
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Домен</label>
                  <input
                    className="form-input"
                    placeholder="okna-moskva.ru"
                    value={formData.domain}
                    onChange={e => setFormData({ ...formData, domain: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Регион</label>
                  <input
                    className="form-input"
                    placeholder="Москва"
                    value={formData.region}
                    onChange={e => setFormData({ ...formData, region: e.target.value })}
                  />
                </div>
              </div>
              <button className="btn btn-primary" type="submit">Создать проект</button>
            </form>
          </div>
        )}

        {loading ? (
          <div className="card-grid">
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton" style={{ height: 120 }} />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📁</div>
            <p>Проектов пока нет</p>
            <p style={{ fontSize: 12, marginTop: 8 }}>Создайте первый проект для начала работы</p>
          </div>
        ) : (
          <div className="card-grid">
            {projects.map(p => (
              <div
                key={p.id}
                className="card"
                onClick={() => navigate(`/project/${p.id}`)}
                style={{ cursor: 'pointer' }}
              >
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                    {p.favicon_url ? (
                      <img src={p.favicon_url} alt="" style={{ width: 20, height: 20, borderRadius: 4 }} />
                    ) : (
                      <span style={{ fontSize: 20 }}>🌐</span>
                    )}
                    <span className="card-title">{p.name}</span>
                  </div>
                  <span className={`badge ${p.is_active ? 'badge-success' : 'badge-neutral'}`}>
                    {p.is_active ? 'Активен' : 'Архив'}
                  </span>
                </div>
                <p style={{ color: 'var(--text-accent)', fontSize: 13, marginBottom: 'var(--space-sm)' }}>
                  {p.domain}
                </p>
                <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                  {p.region || 'Регион не указан'} · {new Date(p.created_at).toLocaleDateString('ru-RU')}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
