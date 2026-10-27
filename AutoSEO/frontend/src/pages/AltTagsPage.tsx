import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { api, AltTagBatch } from '../api/client'

export default function AltTagsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [projects, setProjects] = useState<any[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)

  const [batches, setBatches] = useState<AltTagBatch[]>([])
  const [loading, setLoading] = useState(true)

  const [showModal, setShowModal] = useState(false)
  const [tsvData, setTsvData] = useState('')
  const [importing, setImporting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (!id) {
      setLoadingProjects(true)
      api.getProjects().then(data => setProjects(data.items)).finally(() => setLoadingProjects(false))
    } else {
      loadBatches()
    }
  }, [id])

  const loadBatches = async () => {
    try {
      setLoading(true)
      const data = await api.getAltBatches(id!)
      setBatches(data.items)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    setErrorMsg('')
    if (!tsvData.trim()) {
      setErrorMsg('Вставьте данные')
      return
    }

    // Парсим TSV
    const lines = tsvData.split('\n').map(l => l.trim()).filter(l => l)
    // Убираем заголовок если он есть
    let startIdx = 0
    if (lines[0].toLowerCase().includes('src') || lines[0].toLowerCase().includes('изображени')) {
      startIdx = 1
    }

    const imagesToImport = []
    for (let i = startIdx; i < lines.length; i++) {
      const parts = lines[i].split('\t')
      // Ожидаемые колонки: №, SRC изображения, Страница (где находится)
      // Разделитель \t
      if (parts.length >= 3) {
        imagesToImport.push({
          image_src: parts[1]?.trim(),
          page_url: parts[2]?.trim(),
        })
      } else if (parts.length === 2) {
         // На случай если скопировали без номера
         imagesToImport.push({
          image_src: parts[0]?.trim(),
          page_url: parts[1]?.trim(),
        })
      }
    }

    if (imagesToImport.length === 0) {
      setErrorMsg('Не удалось распознать строки (проверьте формат колонок)')
      return
    }

    try {
      setImporting(true)
      await api.importAltTags(id!, { images: imagesToImport })
      setShowModal(false)
      setTsvData('')
      loadBatches()
    } catch (e: any) {
      setErrorMsg(e.message)
    } finally {
      setImporting(false)
    }
  }

  if (!id) {
    return (
      <>
        <div className="page-header">
          <h1>🖼️ Alt-теги</h1>
          <p className="subtitle">Выберите проект для генерации Alt-тегов</p>
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
                  onClick={() => navigate(`/project/${p.id}/alt-tags`)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="card-header">
                    <span className="card-title">{p.name}</span>
                  </div>
                  <p style={{ color: 'var(--text-accent)', fontSize: 13, marginBottom: 'var(--space-sm)' }}>
                    {p.domain}
                  </p>
                  <button className="btn btn-secondary btn-sm" style={{ width: '100%' }}>Управление alt-тегами →</button>
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
            <h1>🖼️ Генерация Alt-тегов (Vision AI)</h1>
            <p className="subtitle">Массовая обработка изображений сайта</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            ＋ Новая выгрузка
          </button>
        </div>
      </div>

      <div className="page-body">
        {showModal && (
          <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
            <h3 className="card-title" style={{ marginBottom: 'var(--space-sm)' }}>Импорт списка изображений</h3>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
              Скопируйте таблицу из Excel / Screaming Frog и вставьте ниже. Ожидаемые колонки: <strong>№, SRC изображения, Страница, где находится</strong> (разделитель - табуляция).
            </p>
            
            <textarea
              className="form-input"
              style={{ minHeight: 150, fontFamily: 'monospace', fontSize: 13, whiteSpace: 'pre' }}
              value={tsvData}
              onChange={e => setTsvData(e.target.value)}
              placeholder={`1\thttps://example.com/img1.jpg\thttps://example.com/page1\n2\thttps://example.com/img2.png\thttps://example.com/page2`}
            />

            {errorMsg && (
              <div style={{ color: 'var(--danger)', marginTop: 'var(--space-sm)', fontSize: 14 }}>
                {errorMsg}
              </div>
            )}

            <div style={{ display: 'flex', gap: 'var(--space-sm)', marginTop: 'var(--space-md)' }}>
              <button className="btn btn-primary" onClick={handleImport} disabled={importing}>
                {importing ? 'Загрузка...' : 'Загрузить и начать обработку'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Отмена</button>
            </div>
          </div>
        )}

        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>История выгрузок</h3>
          
          {loading ? (
            <div className="skeleton" style={{ height: 200 }} />
          ) : batches.length === 0 ? (
            <div className="empty-state">Нет данных. Сделайте первую выгрузку.</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Дата создания</th>
                    <th>Всего картинок</th>
                    <th>Прогресс</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map(batch => {
                    const percent = batch.total_images ? Math.round((batch.processed_images / batch.total_images) * 100) : 0
                    return (
                      <tr key={batch.id}>
                        <td>{new Date(batch.created_at).toLocaleString('ru-RU')}</td>
                        <td>{batch.total_images}</td>
                        <td style={{ minWidth: 200 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div className="progress-bar-container" style={{ flex: 1, margin: 0, height: 6 }}>
                              <div className="progress-bar-fill" style={{ width: `${percent}%`, background: percent === 100 ? 'var(--success)' : 'var(--primary)' }}></div>
                            </div>
                            <span style={{ fontSize: 12 }}>{percent}%</span>
                          </div>
                        </td>
                        <td>
                          <Link to={`/project/${id}/alt-tags/${batch.id}`} className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: 12 }}>
                            Открыть отчет
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
