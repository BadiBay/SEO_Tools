import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, PaidLink } from '../api/client'

export default function PaidLinkDetailPage() {
  const { id, linkId } = useParams<{ id: string, linkId: string }>()
  const [link, setLink] = useState<PaidLink | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (linkId) {
      loadLink()
    }
  }, [linkId])

  const loadLink = async () => {
    try {
      setLoading(true)
      const data = await api.getPaidLinkDetails(linkId!)
      setLink(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="page-body"><div className="skeleton" style={{ height: 400 }} /></div>
  }

  if (!link) {
    return <div className="page-body"><div className="empty-state">Ссылка не найдена</div></div>
  }

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
          <Link to={`/project/${id}/paid-links`} className="btn btn-secondary">← Назад</Link>
          <span className={`badge badge-${link.status === 'published' ? 'success' : link.status === 'review' ? 'warning' : 'neutral'}`}>
            Статус: {link.status}
          </span>
        </div>
        <h1>Детали статьи для {link.donor_domain}</h1>
      </div>

      <div className="page-body">
        
        {link.status === 'draft' && (
          <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
            <h3>Статья еще не сгенерирована</h3>
            <p className="subtitle">Вернитесь назад и запустите пайплайн генерации статьи.</p>
          </div>
        )}

        {link.article_html && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 'var(--space-lg)' }}>
            
            {/* Editor / Preview Area */}
            <div className="card">
              <h3 className="card-title">Сгенерированная статья</h3>
              
              <div style={{ marginBottom: 'var(--space-md)' }}>
                <strong>Title:</strong> {link.meta_title}
              </div>
              <div style={{ marginBottom: 'var(--space-md)' }}>
                <strong>Description:</strong> {link.meta_description}
              </div>

              <div 
                className="article-preview"
                style={{ 
                  padding: 'var(--space-lg)', 
                  border: '1px solid var(--border-color)', 
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-secondary)',
                  minHeight: 400
                }}
                dangerouslySetInnerHTML={{ __html: link.article_html }}
              />

              {link.status === 'review' && (
                <div style={{ marginTop: 'var(--space-lg)', display: 'flex', gap: 'var(--space-md)' }}>
                  <button className="btn btn-primary" onClick={() => alert('Mock: Утверждено и отправлено в Miralinks!')}>
                    ✓ Утвердить и отправить на публикацию
                  </button>
                  <button className="btn btn-secondary">
                    Перегенерировать
                  </button>
                </div>
              )}
            </div>

            {/* Sidebar metadata */}
            <div>
              <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <h4 style={{ marginBottom: 'var(--space-md)' }}>Качество (AI Check)</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                  <div>
                    {link.tone_check_passed ? '✅' : '⏳'} Tone of Voice
                  </div>
                  <div>
                    {link.structure_check_passed ? '✅' : '⏳'} SEO-структура
                  </div>
                </div>
              </div>

              <div className="card">
                <h4 style={{ marginBottom: 'var(--space-md)' }}>Инструкция вебмастеру</h4>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  {link.webmaster_instructions || 'Нет инструкций'}
                </p>
              </div>
            </div>

          </div>
        )}

      </div>
    </>
  )
}
