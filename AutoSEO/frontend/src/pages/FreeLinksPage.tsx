import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { api, FreeLink, DonorPlatform, Project } from '../api/client'

export default function FreeLinksPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [projects, setProjects] = useState<any[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)

  const [project, setProject] = useState<Project | null>(null)
  const [links, setLinks] = useState<FreeLink[]>([])
  const [donors, setDonors] = useState<DonorPlatform[]>([])
  const [loading, setLoading] = useState(true)

  const [showImportModal, setShowImportModal] = useState(false)
  const [tsvData, setTsvData] = useState('')
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState('')

  // Verify State
  const [verifyingLinkId, setVerifyingLinkId] = useState<string | null>(null)
  const [placedUrlInput, setPlacedUrlInput] = useState('')

  // Project Info Card State
  const [targetUrl, setTargetUrl] = useState('')
  const [promoText, setPromoText] = useState('')
  const [accountData, setAccountData] = useState('')
  const [savingInfo, setSavingInfo] = useState(false)

  // Tabs state
  const [activeTab, setActiveTab] = useState<'placed' | 'donors'>('placed')

  useEffect(() => {
    if (!id) {
      setLoadingProjects(true)
      api.getProjects().then(data => setProjects(data.items)).finally(() => setLoadingProjects(false))
    } else {
      loadData()
    }
  }, [id])

  const loadData = async () => {
    try {
      setLoading(true)
      const [proj, linksData, donorsData] = await Promise.all([
        api.getProject(id!),
        api.getFreeLinks(id!),
        api.getDonors(id!) // only unused donors!
      ])
      setProject(proj)
      setLinks(linksData.items)
      setDonors(donorsData.items)

      // Initialize project info state
      const priors = proj.client_priorities || {}
      setTargetUrl(priors.free_link_target_url || proj.domain)
      setPromoText(priors.free_link_promo_text || '')
      setAccountData(priors.free_link_account_data || '')

    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteLink = async (linkId: string) => {
    if (!window.confirm('Вы уверены, что хотите удалить эту задачу?')) return
    try {
      await api.deleteFreeLink(linkId)
      loadData()
    } catch (e: any) {
      alert('Ошибка при удалении: ' + e.message)
    }
  }

  const handleVerifySubmit = async (linkId: string) => {
    if (!placedUrlInput.trim()) {
      alert('Введите URL размещения')
      return
    }
    try {
      await api.verifyFreeLink(linkId, placedUrlInput)
      setVerifyingLinkId(null)
      setPlacedUrlInput('')
      loadData()
    } catch (e: any) {
      alert('Ошибка: ' + e.message)
    }
  }

  const handleSaveInfo = async () => {
    try {
      setSavingInfo(true)
      await api.updateProjectFreeLinksInfo(id!, {
        target_url: targetUrl,
        promo_text: promoText,
        account_data: accountData
      })
      // No reload needed, just success state
    } catch (e: any) {
      alert('Ошибка при сохранении: ' + e.message)
    } finally {
      setSavingInfo(false)
    }
  }

  const handleImport = async () => {
    setImportError('')
    if (!tsvData.trim()) {
      setImportError('Вставьте данные')
      return
    }

    const lines = tsvData.split('\n').map(l => l.trim()).filter(l => l)
    const donorsToImport = []
    
    // Пытаемся понять, есть ли заголовок
    let startIdx = 0
    if (lines[0].toLowerCase().includes('назван') || lines[0].toLowerCase().includes('url') || lines[0].includes('№')) {
      startIdx = 1
    }

    for (let i = startIdx; i < lines.length; i++) {
      const parts = lines[i].split('\t')
      // Ожидаемые колонки: № | Дата | Ссылка
      if (parts.length >= 3) {
        // We consider "Ссылка" to be placed_url, and we extract domain in backend
        const placed_url = parts[2]?.trim()
        if (placed_url && placed_url.includes('http')) {
          donorsToImport.push({
            name: 'Импортировано', // Backend will replace with domain if not found
            url: placed_url, // Backend will extract root domain from this
            placed_url: placed_url
          })
        }
      } else if (parts.length === 2 && parts[1].includes('http')) {
        // Fallback if they didn't copy "№"
        donorsToImport.push({
          name: 'Импортировано',
          url: parts[1]?.trim(),
          placed_url: parts[1]?.trim()
        })
      }
    }

    if (donorsToImport.length === 0) {
      setImportError('Не удалось распознать строки. Нужны колонки (№ | Дата | Ссылка)')
      return
    }

    try {
      setImporting(true)
      const res = await api.importFreeLinks(id!, { donors: donorsToImport })
      alert(`Успешно! Добавлено новых площадок в общую базу: ${res.created_donors}. Создано задач: ${res.created_links}`)
      setShowImportModal(false)
      setTsvData('')
      loadData()
    } catch (e: any) {
      setImportError(e.message)
    } finally {
      setImporting(false)
    }
  }

  const handlePlaceLink = async (donorId: string) => {
    try {
      await api.createFreeLink({
        project_id: id!,
        donor_id: donorId,
        target_url: targetUrl || project?.domain || ''
      })
      // It becomes pending/generating. We move it to placed.
      loadData()
      setActiveTab('placed')
    } catch (e: any) {
      alert(e.message)
    }
  }

  if (!id) {
    return (
      <>
        <div className="page-header">
          <h1>🔗 Бесплатные ссылки</h1>
          <p className="subtitle">Выберите проект для работы со ссылками</p>
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
                  onClick={() => navigate(`/project/${p.id}/free-links`)}
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
            <h1>🔗 Бесплатные ссылки (Крауд)</h1>
            <p className="subtitle">Размещение ссылок для проекта {project?.name}</p>
          </div>
        </div>
      </div>

      <div className="page-body">
        {showImportModal && (
          <div className="card" style={{ marginBottom: 'var(--space-xl)', border: '1px solid var(--primary)' }}>
            <h3 className="card-title" style={{ marginBottom: 'var(--space-sm)' }}>Массовый импорт размещенных ссылок</h3>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
              Скопируйте таблицу из Excel и вставьте ниже. Ожидаемые колонки: <strong>№ | Дата | Ссылка</strong>.
            </p>
            
            <textarea
              className="form-input"
              style={{ minHeight: 150, fontFamily: 'monospace', fontSize: 13, whiteSpace: 'pre' }}
              value={tsvData}
              onChange={e => setTsvData(e.target.value)}
              placeholder={`1\t08.06.2026\thttps://rentry.co/ita778pd\n2\t13.07.2026\thttps://blogfreely.net/shibargan`}
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

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--space-xl)' }}>
          
          {/* Левая часть: Таблицы */}
          <div>
            <div style={{ display: 'flex', gap: 'var(--space-md)', marginBottom: 'var(--space-md)' }}>
              <button 
                className={`btn ${activeTab === 'placed' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('placed')}
              >
                Размещенные ссылки ({links.length})
              </button>
              <button 
                className={`btn ${activeTab === 'donors' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('donors')}
              >
                Доступные площадки ({donors.length})
              </button>
            </div>

            <div className="card">
              {activeTab === 'placed' && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
                    <h3 className="card-title">История размещений</h3>
                    <button className="btn btn-secondary btn-sm" onClick={() => setShowImportModal(true)}>
                      📥 Массовый импорт
                    </button>
                  </div>
                  {loading ? (
                    <div className="skeleton" style={{ height: 200 }} />
                  ) : links.length === 0 ? (
                    <div className="empty-state">Нет размещенных ссылок</div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th style={{ width: 50 }}>№</th>
                            <th style={{ width: 120 }}>Дата</th>
                            <th>Ссылка (placed URL)</th>
                            <th style={{ width: 80 }}>Статус</th>
                            <th style={{ width: 150, textAlign: 'right' }}>Действия</th>
                          </tr>
                        </thead>
                        <tbody>
                          {links.map((link, idx) => (
                            <tr key={link.id}>
                              <td style={{ color: 'var(--text-muted)' }}>{idx + 1}</td>
                              <td>{new Date(link.placed_at || link.created_at).toLocaleDateString('ru-RU')}</td>
                              <td>
                                {verifyingLinkId === link.id ? (
                                  <div style={{ display: 'flex', gap: 5 }}>
                                    <input 
                                      className="form-input" 
                                      style={{ padding: '4px 8px', fontSize: 13, minHeight: 'auto' }}
                                      placeholder="Вставьте URL размещения..."
                                      value={placedUrlInput}
                                      onChange={e => setPlacedUrlInput(e.target.value)}
                                      autoFocus
                                    />
                                    <button className="btn btn-primary btn-sm" onClick={() => handleVerifySubmit(link.id)}>OK</button>
                                    <button className="btn btn-secondary btn-sm" onClick={() => setVerifyingLinkId(null)}>X</button>
                                  </div>
                                ) : link.placed_url ? (
                                  <a href={link.placed_url} target="_blank" rel="noreferrer" style={{ wordBreak: 'break-all' }}>
                                    {link.placed_url}
                                  </a>
                                ) : (
                                  <span style={{ color: 'var(--text-muted)' }}>Ожидает размещения ({link.donor?.url})</span>
                                )}
                              </td>
                              <td>
                                {link.status === 'verified' ? (
                                  <span className="badge badge-success">✓</span>
                                ) : (
                                  <span className="badge badge-neutral">...</span>
                                )}
                              </td>
                              <td style={{ textAlign: 'right' }}>
                                <div style={{ display: 'flex', gap: 5, justifyContent: 'flex-end' }}>
                                  {!link.placed_url && verifyingLinkId !== link.id && (
                                    <button 
                                      className="btn btn-primary btn-sm" 
                                      onClick={() => { setVerifyingLinkId(link.id); setPlacedUrlInput(''); }}
                                    >
                                      Ввести URL
                                    </button>
                                  )}
                                  <button 
                                    className="btn btn-secondary btn-sm" 
                                    onClick={() => handleDeleteLink(link.id)}
                                    style={{ color: 'var(--danger)', borderColor: 'transparent' }}
                                    title="Удалить"
                                  >
                                    Удалить
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}

              {activeTab === 'donors' && (
                <>
                  <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>Доступные площадки для размещения</h3>
                  {loading ? (
                    <div className="skeleton" style={{ height: 200 }} />
                  ) : donors.length === 0 ? (
                    <div className="empty-state">Нет доступных площадок. Все заняты или база пуста.</div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Название</th>
                            <th>URL донора</th>
                            <th>Тип</th>
                            <th style={{ width: 100 }}>Действия</th>
                          </tr>
                        </thead>
                        <tbody>
                          {donors.map((donor) => (
                            <tr key={donor.id}>
                              <td style={{ fontWeight: 600 }}>{donor.name}</td>
                              <td><a href={donor.url} target="_blank" rel="noreferrer">{donor.url}</a></td>
                              <td>{donor.platform_type}</td>
                              <td>
                                <button 
                                  className="btn btn-primary btn-sm"
                                  onClick={() => handlePlaceLink(donor.id)}
                                >
                                  Разместить
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Правая часть: Карточка проекта */}
          <div>
            <div className="card" style={{ position: 'sticky', top: 'var(--space-xl)' }}>
              <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>
                Данные проекта для размещения
              </h3>
              
              <div className="form-group">
                <label className="form-label">Целевой URL</label>
                <input 
                  type="url"
                  className="form-input"
                  value={targetUrl}
                  onChange={e => setTargetUrl(e.target.value)}
                  placeholder="https://example.com"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Текст для размещения (описание)</label>
                <textarea 
                  className="form-input"
                  style={{ minHeight: 120 }}
                  value={promoText}
                  onChange={e => setPromoText(e.target.value)}
                  placeholder="Например: Шибарган. Окунитесь в мир..."
                />
              </div>

              <div className="form-group">
                <label className="form-label">Данные аккаунта (почта / логин)</label>
                <textarea 
                  className="form-input"
                  style={{ minHeight: 80 }}
                  value={accountData}
                  onChange={e => setAccountData(e.target.value)}
                  placeholder="isanelson1988@aliasvault.net&#10;Пароль: 12345"
                />
              </div>

              <button 
                className="btn btn-primary" 
                style={{ width: '100%' }}
                onClick={handleSaveInfo}
                disabled={savingInfo}
              >
                {savingInfo ? 'Сохранение...' : 'Сохранить данные'}
              </button>
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
