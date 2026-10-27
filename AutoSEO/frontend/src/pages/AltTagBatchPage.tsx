import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, AltTagBatch } from '../api/client'

export default function AltTagBatchPage() {
  const { id, batchId } = useParams<{ id: string; batchId: string }>()
  
  const [batch, setBatch] = useState<AltTagBatch | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    // Simple polling for MVP since it runs in background
    const interval = setInterval(() => {
      api.getAltBatch(batchId!).then(data => {
        setBatch(data)
        if (data.processed_images >= data.total_images) {
          clearInterval(interval)
        }
      })
    }, 5000)

    return () => clearInterval(interval)
  }, [batchId])

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await api.getAltBatch(batchId!)
      setBatch(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const exportCsv = () => {
    if (!batch || !batch.images) return

    // "№", "SRC изображения", "Страница, где находится", "Сгенерированный Alt"
    let csvContent = "№\tSRC изображения\tСтраница, где находится\tСгенерированный Alt\n"
    batch.images.forEach((img, idx) => {
      csvContent += `${idx + 1}\t${img.image_src}\t${img.page_url || ''}\t${img.generated_alt || img.original_alt || ''}\n`
    })

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `alt_tags_batch_${batch.id.substring(0, 8)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (loading) return <div className="page-body">Загрузка...</div>
  if (!batch) return <div className="page-body">Выгрузка не найдена</div>

  const isCompleted = batch.processed_images >= batch.total_images

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
          <Link to={`/project/${id}/alt-tags`} className="btn btn-secondary">← Назад к списку</Link>
          {!isCompleted && <span className="badge badge-info">Обработка ИИ...</span>}
          {isCompleted && <span className="badge badge-success">Готово</span>}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Выгрузка картинок от {new Date(batch.created_at).toLocaleDateString('ru-RU')}</h1>
            <p className="subtitle">Обработано {batch.processed_images} из {batch.total_images} (Пропущено SVG/иконок: {batch.skipped_svg})</p>
          </div>
          <button className="btn btn-primary" onClick={exportCsv} disabled={!isCompleted && batch.processed_images === 0}>
            📥 Экспорт результата (CSV)
          </button>
        </div>
      </div>

      <div className="page-body">
        <div className="card">
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 100 }}>Превью</th>
                  <th style={{ width: '30%' }}>Сырые данные (URL / Страница)</th>
                  <th style={{ width: '15%' }}>Статус</th>
                  <th style={{ width: '40%' }}>Сгенерированный Alt</th>
                </tr>
              </thead>
              <tbody>
                {batch.images?.map(img => (
                  <tr key={img.id}>
                    <td>
                      <div style={{ width: 80, height: 80, background: 'var(--bg-secondary)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                        {img.image_type !== 'vector' && img.image_type !== 'icon' ? (
                          <img src={img.image_src} alt="" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} loading="lazy" />
                        ) : (
                          <span style={{ fontSize: 24, opacity: 0.5 }}>{img.image_type === 'vector' ? 'SVG' : 'ICON'}</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div style={{ fontSize: 13, wordBreak: 'break-all' }}>
                        <div style={{ marginBottom: 4 }}><a href={img.image_src} target="_blank" rel="noreferrer">{img.image_src}</a></div>
                        {img.page_url && (
                          <div style={{ color: 'var(--text-muted)' }}>
                            Страница: <a href={img.page_url} target="_blank" rel="noreferrer" style={{ color: 'var(--text-muted)' }}>{img.page_url}</a>
                          </div>
                        )}
                        {img.original_alt && (
                          <div style={{ marginTop: 4, color: img.original_alt_is_junk ? 'var(--danger)' : 'var(--text-secondary)' }}>
                            Старый alt: {img.original_alt} {img.original_alt_is_junk && '(мусор)'}
                          </div>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-${
                        img.status === 'done' ? 'success' : 
                        img.status === 'error' ? 'danger' :
                        img.status === 'skipped' ? 'neutral' : 'info'
                      }`}>
                        {img.status}
                      </span>
                    </td>
                    <td>
                      {img.status === 'done' ? (
                        <div style={{ background: 'var(--bg-secondary)', padding: 'var(--space-sm)', borderRadius: 4, fontSize: 14 }}>
                          {img.generated_alt}
                        </div>
                      ) : img.status === 'error' ? (
                        <div style={{ color: 'var(--danger)', fontSize: 13 }}>{img.error_message}</div>
                      ) : img.status === 'skipped' ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{img.error_message}</div>
                      ) : (
                        <div className="skeleton" style={{ height: 40, width: '100%' }} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
