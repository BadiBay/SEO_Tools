import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { api, PaidLink, DonorPlatform } from '../api/client'

export default function PaidLinksPage() {
  const { id } = useParams<{ id: string }>()
  const [links, setLinks] = useState<PaidLink[]>([])
  const [donors, setDonors] = useState<DonorPlatform[]>([])
  const [loading, setLoading] = useState(true)

  // Form state
  const [showForm, setShowForm] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [donorDomain, setDonorDomain] = useState('')
  const [formError, setFormError] = useState('')

  // Import state
  const [showImportModal, setShowImportModal] = useState(false)
  const [tsvData, setTsvData] = useState('')
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState('')

  useEffect(() => {
    if (id) {
      loadLinks()
    }
  }, [id])

  const loadLinks = async () => {
    try {
      setLoading(true)
      const [linksData, donorsData] = await Promise.all([
        api.getPaidLinks(id!),
        api.getPaidDonors(id!)
      ])
      setLinks(linksData.items)
      setDonors(donorsData.items)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    try {
      await api.createPaidLink({
        project_id: id!,
        main_keyword: keyword,
        donor_domain: donorDomain
      })
      setShowForm(false)
      setKeyword('')
      setDonorDomain('')
      loadLinks()
    } catch (e: any) {
      setFormError(e.message)
    }
  }

  const handleGenerate = async (linkId: string) => {
    try {
      await api.generatePaidLinkArticle(linkId)
      // Optimistic update
      setLinks(links.map(l => l.id === linkId ? { ...l, status: 'generating' } : l))
    } catch (e) {
      alert('Ошибка запуска генерации')
    }
  }

  const handleImport = async () => {
    setImportError('')
    if (!tsvData.trim()) {
      setImportError('Вставьте данные')
      return
    }

    const lines = tsvData.split('\n').map(l => l.trim()).filter(l => l)
    const linksToImport = []
    
    // Пытаемся понять, есть ли заголовок
    let startIdx = 0
    if (lines[0].toLowerCase().includes('назван') || lines[0].toLowerCase().includes('url') || lines[0].includes('№')) {
      startIdx = 1
    }

    for (let i = startIdx; i < lines.length; i++) {
      const parts = lines[i].split('\t')
      // Ожидаемые колонки: № | Дата | Донор (URL) | Ссылка (URL размещения) | Цена
      if (parts.length >= 3) {
        let domain = parts[2]?.trim()
        let placed_url = parts.length >= 4 ? parts[3]?.trim() : undefined
        let priceStr = parts.length >= 5 ? parts[4]?.trim() : undefined
        
        // If domain is missing but placed_url exists, fallback
        if (!domain && placed_url) {
            domain = placed_url
        }

        if (domain) {
          linksToImport.push({
            domain: domain,
            placed_url: placed_url && placed_url.includes('http') ? placed_url : undefined,
            price: priceStr ? parseFloat(priceStr.replace(/[^0-9.]/g, '')) || undefined : undefined
          })
        }
      } else if (parts.length === 2) {
        // Fallback for simple domain-only lists
        linksToImport.push({
          domain: parts[1]?.trim()
        })
      }
    }

    if (linksToImport.length === 0) {
      setImportError('Не удалось распознать строки. Нужны колонки (№ | Дата | Донор | Ссылка | Цена)')
      return
    }

    try {
      setImporting(true)
      const res = await api.importPaidLinks(id!, { links: linksToImport })
      alert(`Успешно! Добавлено новых площадок в базу: ${res.created_donors}. Создано платных ссылок: ${res.created_links}`)
      setShowImportModal(false)
      setTsvData('')
      loadLinks()
    } catch (e: any) {
      setImportError(e.message)
    } finally {
      setImporting(false)
    }
  }

  const [projects, setProjects] = useState<any[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!id) {
      setLoadingProjects(true)
      api.getProjects().then(data => setProjects(data.items)).finally(() => setLoadingProjects(false))
    }
  }, [id])

  if (!id) {
    return (
      <>
        <div className="page-header">
          <h1>💸 Платные ссылки / Аутрич</h1>
          <p className="subtitle">Выберите проект для управления ссылками</p>
        </div>
        <div className="page-body">
          {loadingProjects ? (
            <div className="card-grid">
              {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 120 }} />)}
            </div>
          ) : projects.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📁</div>
              <p>Сначала создайте проект в главном разделе</p>
            </div>
          ) : (
            <div className="card-grid">
              {projects.map(p => (
                <div
                  key={p.id}
                  className="card"
                  onClick={() => navigate(`/project/${p.id}/paid-links`)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="card-header">
                    <span className="card-title">{p.name}</span>
                  </div>
                  <p style={{ color: 'var(--text-accent)', fontSize: 13, marginBottom: 'var(--space-sm)' }}>
                    {p.domain}
                  </p>
                  <button className="btn btn-secondary btn-sm" style={{ width: '100%' }}>Управление ссылками →</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </>
    )
  }

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>💸 Платные ссылки / Аутрич</h1>
            <p className="subtitle">Управление генерацией SEO-статей и размещением</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Отмена' : '＋ Добавить ссылку'}
          </button>
        </div>
      </div>

      <div className="page-body">
        {showImportModal && (
          <div className="card" style={{ marginBottom: 'var(--space-xl)', border: '1px solid var(--primary)' }}>
            <h3 className="card-title" style={{ marginBottom: 'var(--space-sm)' }}>Массовый импорт платных ссылок</h3>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
              Скопируйте таблицу из Excel/Miralinks и вставьте ниже. Ожидаемые колонки: <strong>№ | Дата | Донор | Ссылка размещения | Цена</strong>.
            </p>
            
            <textarea
              className="form-input"
              style={{ minHeight: 150, fontFamily: 'monospace', fontSize: 13, whiteSpace: 'pre' }}
              value={tsvData}
              onChange={e => setTsvData(e.target.value)}
              placeholder={`1\t08.06.2026\tvc.ru\thttps://vc.ru/article\t5000\n2\t13.07.2026\thabr.com\thttps://habr.com/post\t10000`}
            />

            {importError && (
              <div style={{ color: 'var(--danger)', marginTop: 'var(--space-sm)', fontSize: 14 }}>
                {importError}
              </div>
            )}

            <div style={{ display: 'flex', gap: 'var(--space-sm)', marginTop: 'var(--space-md)' }}>
              <button className="btn btn-primary" onClick={handleImport} disabled={importing}>
                {importing ? 'Загрузка...' : 'Загрузить базу'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowImportModal(false)}>Отмена</button>
            </div>
          </div>
        )}

        {showForm && (
          <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
            <h3 className="card-title">Новая ссылка</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Продвигаемый запрос (Анкор)</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="например: купить пластиковые окна"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Домен донора</label>
                <input 
                  type="text" 
                  className="form-input" 
                  list="donors-list"
                  value={donorDomain}
                  onChange={(e) => setDonorDomain(e.target.value)}
                  placeholder="например: vc.ru"
                  required
                />
                <datalist id="donors-list">
                  {donors.map(d => (
                    <option key={d.id} value={d.url.replace('https://', '').replace('http://', '').replace('/', '')} />
                  ))}
                </datalist>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                  Выберите домен из неиспользованных площадок или введите новый.
                </p>
              </div>

              {formError && (
                <div style={{ color: 'var(--danger)', marginBottom: 'var(--space-md)', fontSize: 14 }}>
                  {formError}
                </div>
              )}

              <button type="submit" className="btn btn-primary">Создать заявку</button>
            </form>
          </div>
        )}

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
            <h3 className="card-title">Запланированные и купленные ссылки</h3>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowImportModal(true)}>
              📥 Массовый импорт
            </button>
          </div>
          
          {loading ? (
            <div className="skeleton" style={{ height: 200 }} />
          ) : links.length === 0 ? (
            <div className="empty-state">Пока нет добавленных ссылок</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Донор</th>
                    <th>Анкор / Кластер</th>
                    <th>Цена</th>
                    <th>Статус</th>
                    <th>Дата</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {links.map(link => (
                    <tr key={link.id}>
                      <td style={{ fontWeight: 600 }}>{link.donor_domain}</td>
                      <td>ID кластера: {link.cluster_id?.substring(0, 8)}</td>
                      <td>{link.price ? `${link.price} ₽` : '-'}</td>
                      <td>
                        <span className={`badge badge-${
                          link.status === 'published' ? 'success' : 
                          link.status === 'review' ? 'warning' : 'neutral'
                        }`}>
                          {link.status}
                        </span>
                      </td>
                      <td>{new Date(link.created_at).toLocaleDateString('ru-RU')}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 8 }}>
                          {link.status === 'draft' && (
                            <button className="btn btn-secondary" onClick={() => handleGenerate(link.id)} style={{ padding: '4px 8px', fontSize: 12 }}>
                              ▶ Сгенерировать статью
                            </button>
                          )}
                          <Link to={`/project/${id}/paid-links/${link.id}`} className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: 12 }}>
                            Открыть
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
