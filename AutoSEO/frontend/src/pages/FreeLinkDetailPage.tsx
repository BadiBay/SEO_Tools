import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, FreeLink, Project } from '../api/client'

export default function FreeLinkDetailPage() {
  const { id, linkId } = useParams<{ id: string; linkId: string }>()
  
  const [link, setLink] = useState<FreeLink | null>(null)
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  
  const [placedUrl, setPlacedUrl] = useState('')
  const [verifyMsg, setVerifyMsg] = useState('')

  useEffect(() => {
    loadData()
  }, [id, linkId])

  const loadData = async () => {
    try {
      setLoading(true)
      const [linkData, projData] = await Promise.all([
        api.getFreeLinks(id!).then(res => res.items.find(l => l.id === linkId) || null),
        api.getProject(id!)
      ])
      setLink(linkData)
      setProject(projData)
      if (linkData?.placed_url) {
        setPlacedUrl(linkData.placed_url)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    try {
      await api.generateFreeLinkAssets(linkId!)
      setLink(prev => prev ? { ...prev, status: 'generating' } : prev)
      // В реальном приложении здесь был бы поллинг или WebSockets
      setTimeout(loadData, 5000) 
    } catch (e) {
      alert('Ошибка генерации')
    }
  }

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setVerifyMsg('')
    try {
      await api.verifyFreeLink(linkId!, { placed_url: placedUrl })
      setVerifyMsg('Проверка запущена! (статус обновится в фоне)')
      setLink(prev => prev ? { ...prev, status: 'verifying', placed_url: placedUrl } : prev)
      setTimeout(loadData, 3000)
    } catch (e: any) {
      alert(e.message || 'Ошибка проверки')
    }
  }

  if (loading) return <div className="page-body">Загрузка...</div>
  if (!link) return <div className="page-body">Ссылка не найдена</div>

  const isGenerating = link.status === 'generating'
  const isReady = link.status === 'ready_for_placement' || link.status === 'placed' || link.status === 'verified'

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
          <Link to={`/project/${id}/free-links`} className="btn btn-secondary">← Назад</Link>
          <span className={`badge badge-${
            link.status === 'verified' ? 'success' : 
            link.status === 'dead' ? 'danger' :
            link.status === 'ready_for_placement' ? 'info' : 'neutral'
          }`}>
            Статус: {link.status}
          </span>
        </div>
        <h1>Площадка: {link.donor?.name || '—'}</h1>
        <p className="subtitle">
          Тип: {link.donor?.platform_type} | 
          <a href={link.donor?.url} target="_blank" rel="noreferrer" style={{ marginLeft: 8 }}>
            Перейти на донор →
          </a>
        </p>
      </div>

      <div className="page-body">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xl)' }}>
          
          {/* Левая колонка: Подготовка и данные */}
          <div>
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
                <h3 className="card-title">1. Данные для регистрации</h3>
                {link.status === 'pending' && (
                  <button className="btn btn-primary btn-sm" onClick={handleGenerate} disabled={isGenerating}>
                    {isGenerating ? 'Генерация...' : 'Сгенерировать данные'}
                  </button>
                )}
              </div>
              
              {!isReady && !isGenerating && (
                <div className="empty-state" style={{ padding: 'var(--space-md)' }}>
                  Нажмите кнопку выше, чтобы ИИ подготовил email, пароль и уникальный текст для площадки.
                </div>
              )}
              
              {isGenerating && (
                <div className="skeleton" style={{ height: 150 }} />
              )}
              
              {isReady && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: 12 }}>Уникальный Email и пароль (для регистрации)</label>
                    <div style={{ background: 'var(--bg-secondary)', padding: 'var(--space-sm)', borderRadius: 6, fontFamily: 'monospace', fontSize: 14 }}>
                      {link.email_alias || '—'}
                    </div>
                  </div>
                  
                  {link.donor?.requires_logo && project?.client_logo_url && (
                    <div className="form-group">
                      <label className="form-label" style={{ fontSize: 12 }}>Логотип для профиля</label>
                      <div style={{ background: 'var(--bg-secondary)', padding: 'var(--space-sm)', borderRadius: 6 }}>
                        <img src={project.client_logo_url} alt="Logo" style={{ maxHeight: 60, maxWidth: 150 }} />
                        <div style={{ marginTop: 8 }}>
                          <a href={project.client_logo_url} download target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
                            Скачать логотип
                          </a>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: 12 }}>Целевой URL</label>
                    <div style={{ background: 'var(--bg-secondary)', padding: 'var(--space-sm)', borderRadius: 6, fontSize: 14 }}>
                      {link.target_url}
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: 12 }}>Сгенерированный текст поста/описания</label>
                    <div style={{ background: 'var(--bg-secondary)', padding: 'var(--space-md)', borderRadius: 6, fontSize: 14, whiteSpace: 'pre-wrap' }}>
                      {link.promo_text || '—'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Правая колонка: Размещение и контроль */}
          <div>
            <div className="card" style={{ opacity: isReady ? 1 : 0.5, pointerEvents: isReady ? 'auto' : 'none' }}>
              <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>2. Размещение и мониторинг</h3>
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 'var(--space-lg)' }}>
                Зарегистрируйтесь на сайте донора, разместите подготовленный текст со ссылкой и укажите итоговый URL ниже. Система возьмет его на мониторинг.
              </p>
              
              <form onSubmit={handleVerify}>
                <div className="form-group">
                  <label className="form-label">URL размещенной ссылки</label>
                  <input 
                    type="url" 
                    className="form-input" 
                    value={placedUrl}
                    onChange={e => setPlacedUrl(e.target.value)}
                    placeholder="https://donor.com/my-profile-123"
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary" disabled={link.status === 'verifying'}>
                  {link.status === 'verifying' ? 'Проверка...' : 'Зафиксировать и Проверить'}
                </button>
                {verifyMsg && <span style={{ marginLeft: 16, fontSize: 13, color: 'var(--text-muted)' }}>{verifyMsg}</span>}
              </form>

              {link.last_checked_at && (
                <div style={{ marginTop: 'var(--space-xl)', borderTop: '1px solid var(--border-color)', paddingTop: 'var(--space-md)' }}>
                  <h4 style={{ fontSize: 14, marginBottom: 'var(--space-sm)' }}>Статус мониторинга</h4>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>
                    <li style={{ marginBottom: 4 }}>
                      <strong>Последняя проверка HTTP:</strong> {new Date(link.last_checked_at).toLocaleString('ru-RU')}
                    </li>
                    <li style={{ marginBottom: 4 }}>
                      <strong>Код ответа:</strong> {link.last_http_code ? (
                        <span style={{ color: link.last_http_code === 200 ? 'var(--success)' : 'var(--danger)' }}>
                          {link.last_http_code}
                        </span>
                      ) : '—'}
                    </li>
                    <li>
                      <strong>Google Indexing API:</strong> {link.is_indexed ? '✅ Отправлено' : '—'}
                    </li>
                  </ul>
                </div>
              )}
            </div>
          </div>
          
        </div>
      </div>
    </>
  )
}
