import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api, PipelineRun, Competitor, CompetitorReport } from '../api/client'

interface RunStep {
  step_number: number;
  step_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
}

export default function AnalysisPage() {
  const [searchParams] = useSearchParams()
  const runId = searchParams.get('run')

  const [run, setRun] = useState<(PipelineRun & { steps?: RunStep[] }) | null>(null)
  const [report, setReport] = useState<CompetitorReport | null>(null)
  const [loading, setLoading] = useState(false)

  const loadRun = useCallback(async () => {
    if (!runId) return
    setLoading(true)
    try {
      const data = await api.getRunStatus(runId)
      setRun(data as PipelineRun & { steps?: RunStep[] })

      if (data.status === 'completed') {
        try {
          const rep = await api.getReportByRun(runId)
          setReport(rep)
        } catch {
          // report may not exist yet
        }
      }
    } catch {
      // skip
    } finally {
      setLoading(false)
    }
  }, [runId])

  // Polling for running pipelines
  useEffect(() => {
    loadRun()
    const interval = setInterval(() => {
      if (run?.status === 'running' || run?.status === 'pending') {
        loadRun()
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [runId, run?.status, loadRun])

  // WebSocket for real-time updates
  useEffect(() => {
    if (!runId) return
    let ws: WebSocket | null = null
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      ws = new WebSocket(`${protocol}//${window.location.host}/ws/runs/${runId}`)
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        setRun(prev => prev ? { ...prev, ...data } : prev)
        if (data.status === 'completed') {
          loadRun() // Reload to get report
        }
      }
    } catch {
      // WebSocket not available, fall back to polling
    }
    return () => { ws?.close() }
  }, [runId, loadRun])

  const [projects, setProjects] = useState<any[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!runId) {
      setLoadingProjects(true)
      api.getProjects().then(data => setProjects(data.items)).finally(() => setLoadingProjects(false))
    }
  }, [runId])

  if (!runId) {
    return (
      <>
        <div className="page-header">
          <h1>🔍 Анализ конкурентов</h1>
          <p className="subtitle">Выберите проект для запуска анализа</p>
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
                  onClick={() => navigate(`/project/${p.id}`)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="card-header">
                    <span className="card-title">{p.name}</span>
                  </div>
                  <p style={{ color: 'var(--text-accent)', fontSize: 13, marginBottom: 'var(--space-sm)' }}>
                    {p.domain}
                  </p>
                  <button className="btn btn-secondary btn-sm" style={{ width: '100%' }}>Выбрать проект →</button>
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
        <h1>🔍 Анализ конкурентов</h1>
        {run?.progress && (
          <p className="subtitle">{run.progress.message}</p>
        )}
      </div>

      <div className="page-body">
        {/* Progress */}
        {run && (run.status === 'running' || run.status === 'pending') && (
          <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
              <h3 className="card-title">⏳ Выполнение пайплайна</h3>
              <span className="badge badge-info">{run.progress?.percent || 0}%</span>
            </div>

            <div className="progress-bar" style={{ height: 8, marginBottom: 'var(--space-lg)' }}>
              <div className="progress-bar-fill" style={{ width: `${run.progress?.percent || 0}%` }} />
            </div>

            {/* Steps timeline */}
            {run.steps && run.steps.length > 0 && (
              <div className="step-timeline">
                {run.steps.map((step: RunStep) => (
                  <div key={step.step_number} className={`step-item ${step.status}`}>
                    <div className={`step-number ${step.status}`}>{step.step_number}</div>
                    <span>{step.step_name}</span>
                    <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
                      {step.status === 'completed' ? '✓' : step.status === 'running' ? '⟳' : step.status === 'failed' ? '✗' : '—'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {run?.status === 'failed' && (
          <div className="card" style={{ borderColor: 'var(--danger)', marginBottom: 'var(--space-xl)' }}>
            <h3 style={{ color: 'var(--danger)', marginBottom: 'var(--space-sm)' }}>❌ Ошибка</h3>
            <p style={{ color: 'var(--text-secondary)' }}>{run.error_message}</p>
          </div>
        )}

        {/* Report */}
        {report && (
          <>
            {/* Summary stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
              <div className="stat-card">
                <div className="stat-label">Найдено</div>
                <div className="stat-value">{report.total_competitors}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Прямые конкуренты</div>
                <div className="stat-value">{report.direct_competitors_count}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Маркерных запросов</div>
                <div className="stat-value">{report.marker_queries_count}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Дата анализа</div>
                <div className="stat-value" style={{ fontSize: 14 }}>
                  {new Date(report.created_at).toLocaleDateString('ru-RU')}
                </div>
              </div>
            </div>

            {/* Competitors table */}
            <div className="card">
              <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>Конкуренты</h3>
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Домен</th>
                      <th>Статус</th>
                      <th>Трафик</th>
                      <th>Видимость</th>
                      <th>Тренд</th>
                      <th>DR</th>
                      <th>Беклинки</th>
                      <th>PPC</th>
                      <th>Возраст</th>
                      <th>Семантика</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.competitors.map((c: Competitor) => (
                      <tr key={c.id}>
                        <td>
                          <a href={`https://${c.domain}`} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600 }}>
                            {c.domain}
                          </a>
                        </td>
                        <td>
                          <span className={`badge ${c.is_direct_competitor ? 'badge-success' : 'badge-neutral'}`}>
                            {c.is_direct_competitor ? 'Конкурент' : 'Нет'}
                          </span>
                        </td>
                        <td>{c.traffic_keys_so?.toLocaleString('ru-RU') ?? '—'}</td>
                        <td>{c.visibility_keys_so?.toLocaleString('ru-RU') ?? '—'}</td>
                        <td>
                          {c.visibility_color && (
                            <span>
                              <span className={`trend-dot ${c.visibility_color}`} />
                              {c.visibility_trend === 'growth' ? 'Рост' :
                               c.visibility_trend === 'decline' ? 'Падение' : 'Стагнация'}
                            </span>
                          )}
                        </td>
                        <td>{c.semrush_domain_rating ?? '—'}</td>
                        <td>{c.semrush_backlinks_count?.toLocaleString('ru-RU') ?? '—'}</td>
                        <td>
                          {c.has_ppc ? (
                            <span>
                              <span className="badge badge-warning">PPC</span>
                              {c.ppc_budget_estimate && (
                                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 4 }}>
                                  {c.ppc_budget_estimate.toLocaleString('ru-RU')} ₽
                                </span>
                              )}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>—</span>
                          )}
                        </td>
                        <td>{c.domain_age_years ? `${c.domain_age_years} лет` : '—'}</td>
                        <td>
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                            {c.has_brand_queries && <span className="badge badge-info" style={{ fontSize: 9 }}>БРЕНД</span>}
                            {c.has_commercial_queries && <span className="badge badge-success" style={{ fontSize: 9 }}>КОММ</span>}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {loading && !run && (
          <div className="card">
            <div className="skeleton" style={{ height: 200 }} />
          </div>
        )}
      </div>
    </>
  )
}
