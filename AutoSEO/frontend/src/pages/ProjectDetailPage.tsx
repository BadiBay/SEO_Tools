import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Project, PipelineRun } from '../api/client'

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [loading, setLoading] = useState(true)
  const [launching, setLaunching] = useState(false)
  const [directions, setDirections] = useState('')

  useEffect(() => {
    if (id) loadData(id)
  }, [id])

  async function loadData(projectId: string) {
    try {
      const [proj, projectRuns] = await Promise.all([
        api.getProject(projectId),
        api.getProjectRuns(projectId),
      ])
      setProject(proj)
      setRuns(projectRuns)
      if (proj.client_priorities?.directions) {
        setDirections((proj.client_priorities.directions as string[]).join(', '))
      }
    } catch {
      // skip
    } finally {
      setLoading(false)
    }
  }

  async function handleLaunchAnalysis() {
    if (!id) return
    setLaunching(true)
    try {
      // Сохраняем приоритеты
      if (directions.trim()) {
        await api.savePriorities({
          project_id: id,
          directions: directions.split(',').map(d => d.trim()).filter(Boolean),
        })
      }
      // Запускаем анализ
      const run = await api.startAnalysis({ project_id: id })
      navigate(`/competitors?run=${run.id}`)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Ошибка запуска')
    } finally {
      setLaunching(false)
    }
  }

  const statusLabels: Record<string, { label: string; cls: string }> = {
    pending: { label: 'Ожидание', cls: 'badge-neutral' },
    running: { label: 'Выполняется', cls: 'badge-info' },
    completed: { label: 'Завершён', cls: 'badge-success' },
    failed: { label: 'Ошибка', cls: 'badge-danger' },
  }

  const moduleLabels: Record<string, string> = {
    competitors: '🔍 Анализ конкурентов',
    free_links: '🔗 Бесплатные ссылки',
    paid_links: '💰 Платные ссылки',
    alt_tags: '🖼️ Alt-теги',
  }

  if (loading) return <div className="page-body"><div className="skeleton" style={{ height: 300 }} /></div>
  if (!project) return <div className="page-body"><p>Проект не найден</p></div>

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/')}>← Назад</button>
          <div>
            <h1>{project.name}</h1>
            <p className="subtitle">{project.domain} · {project.region || 'Регион не указан'}</p>
          </div>
        </div>
      </div>

      <div className="page-body">
        {/* Статистика */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
          <div className="stat-card">
            <div className="stat-label">Запусков</div>
            <div className="stat-value">{runs.length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Завершено</div>
            <div className="stat-value">{runs.filter(r => r.status === 'completed').length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">В процессе</div>
            <div className="stat-value">{runs.filter(r => r.status === 'running').length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Создан</div>
            <div className="stat-value" style={{ fontSize: 16 }}>
              {new Date(project.created_at).toLocaleDateString('ru-RU')}
            </div>
          </div>
        </div>

        {/* Запуск анализа */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
          <div className="card">
            <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>🚀 Анализ конкурентов</h3>
            <div className="form-group">
              <label className="form-label">Маржинальные направления бизнеса</label>
              <input
                className="form-input"
                placeholder="окна ПВХ, балконы, двери (через запятую)"
                value={directions}
                onChange={e => setDirections(e.target.value)}
              />
              <p style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 4 }}>
                AI будет генерировать маркерные запросы
              </p>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleLaunchAnalysis}
              disabled={launching}
            >
              {launching ? '⏳ Запуск...' : '▶ Запустить анализ'}
            </button>
          </div>

          <div className="card">
            <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>💰 Платные ссылки</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
              Управление генерацией SEO-статей, анкор-листами и отслеживание купленных ссылок (аутрич / биржи).
            </p>
            <button
              className="btn btn-secondary"
              onClick={() => navigate(`/project/${id}/paid-links`)}
            >
              Перейти к ссылкам →
            </button>
          </div>
        </div>

        {/* История запусков */}
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>📋 История запусков</h3>
          {runs.length === 0 ? (
            <div className="empty-state">
              <p>Запусков пока нет</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Модуль</th>
                  <th>Статус</th>
                  <th>Прогресс</th>
                  <th>Дата</th>
                </tr>
              </thead>
              <tbody>
                {runs.map(run => {
                  const st = statusLabels[run.status] || statusLabels.pending
                  return (
                    <tr key={run.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/competitors?run=${run.id}`)}>
                      <td>{moduleLabels[run.module_type] || run.module_type}</td>
                      <td><span className={`badge ${st.cls}`}>{st.label}</span></td>
                      <td>
                        {run.progress && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                            <div className="progress-bar" style={{ width: 120 }}>
                              <div className="progress-bar-fill" style={{ width: `${run.progress.percent}%` }} />
                            </div>
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                              {run.progress.percent}%
                            </span>
                          </div>
                        )}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                        {new Date(run.created_at).toLocaleString('ru-RU')}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}
