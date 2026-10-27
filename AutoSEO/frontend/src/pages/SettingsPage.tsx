import { useState, useEffect } from 'react'
import { api } from '../api/client'

type KeyStatus = 'active' | 'exhausted'
type ServiceKey = { value: string; status: KeyStatus }
type ServiceConfig = { model: string; keys: ServiceKey[] }

export default function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Service states
  const [gemini, setGemini] = useState<ServiceConfig>({ model: 'gemini-2.5-flash', keys: [] })
  const [openai, setOpenAI] = useState<ServiceConfig>({ model: 'gpt-4o', keys: [] })
  const [anthropic, setAnthropic] = useState<ServiceConfig>({ model: 'claude-3-5-sonnet-20240620', keys: [] })
  const [keysSo, setKeysSo] = useState<ServiceConfig>({ model: '', keys: [] })
  const [semrush, setSemrush] = useState<ServiceConfig>({ model: '', keys: [] })
  const [perplexity, setPerplexity] = useState<ServiceConfig>({ model: 'sonar-pro', keys: [] })
  const [serper, setSerper] = useState<ServiceConfig>({ model: '', keys: [] })

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = await api.getSettings()
      
      const parseConfig = (val: any, defaultModel: string): ServiceConfig => {
        if (!val) return { model: defaultModel, keys: [] }
        if (typeof val === 'string') return { model: defaultModel, keys: [{ value: val, status: 'active' }] } // fallback
        return {
          model: val.model || defaultModel,
          keys: Array.isArray(val.keys) ? val.keys : []
        }
      }

      setGemini(parseConfig(data.gemini_settings || data.gemini_api_key, 'gemini-2.5-flash'))
      setOpenAI(parseConfig(data.openai_settings || data.openai_api_key, 'gpt-4o'))
      setAnthropic(parseConfig(data.anthropic_settings || data.anthropic_api_key, 'claude-3-5-sonnet-20240620'))
      setKeysSo(parseConfig(data.keys_so_settings || data.keys_so_api_key, ''))
      setSemrush(parseConfig(data.semrush_settings || data.semrush_api_key, ''))
      setPerplexity(parseConfig(data.perplexity_settings || data.perplexity_api_key, 'sonar-pro'))
      setSerper(parseConfig(data.serper_settings || data.serper_api_key, ''))
      
    } catch (e) {
      console.error("Failed to load settings", e)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      const updates = [
        { key: 'gemini_settings', value: gemini },
        { key: 'openai_settings', value: openai },
        { key: 'anthropic_settings', value: anthropic },
        { key: 'keys_so_settings', value: keysSo },
        { key: 'semrush_settings', value: semrush },
        { key: 'perplexity_settings', value: perplexity },
        { key: 'serper_settings', value: serper }
      ]
      await api.updateSettings(updates)
      alert('Настройки успешно сохранены!')
      loadSettings()
    } catch (e: any) {
      alert('Ошибка при сохранении: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  const renderServiceSection = (
    title: string, 
    desc: string, 
    config: ServiceConfig, 
    setConfig: React.Dispatch<React.SetStateAction<ServiceConfig>>,
    models?: string[]
  ) => {
    return (
      <div style={{ marginBottom: 'var(--space-2xl)' }}>
        <h3 style={{ marginBottom: 4 }}>{title}</h3>
        <p className="subtitle" style={{ marginBottom: 'var(--space-md)' }}>{desc}</p>
        
        {models && models.length > 0 && (
          <div className="form-group">
            <label className="form-label">Модель по умолчанию</label>
            <select 
              className="form-select" 
              value={config.model} 
              onChange={e => setConfig({ ...config, model: e.target.value })}
              style={{ width: 250 }}
            >
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
        )}

        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-sm)' }}>
            <label className="form-label" style={{ marginBottom: 0 }}>Список ключей (с ротацией)</label>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => setConfig({ ...config, keys: [...config.keys, { value: '', status: 'active' }] })}
            >
              + Добавить ключ
            </button>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {config.keys.map((k, idx) => (
              <div key={idx} style={{ display: 'flex', gap: 8, alignItems: 'center', background: 'var(--bg-secondary)', padding: 'var(--space-sm)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <input 
                  className="form-input" 
                  style={{ flex: 1, margin: 0, padding: '8px 12px' }}
                  type="password"
                  placeholder="Вставьте ключ API..."
                  value={k.value}
                  onChange={e => {
                    const newKeys = [...config.keys]
                    newKeys[idx].value = e.target.value
                    setConfig({ ...config, keys: newKeys })
                  }}
                />
                
                <select 
                  className="form-select"
                  style={{ width: 140, padding: '8px 12px', margin: 0, 
                           color: k.status === 'active' ? 'var(--success)' : 'var(--danger)',
                           borderColor: k.status === 'active' ? 'var(--success)' : 'var(--danger)' }}
                  value={k.status}
                  onChange={e => {
                    const newKeys = [...config.keys]
                    newKeys[idx].status = e.target.value as KeyStatus
                    setConfig({ ...config, keys: newKeys })
                  }}
                >
                  <option value="active">✓ Активен</option>
                  <option value="exhausted">❌ Исчерпан</option>
                </select>

                <button 
                  className="btn btn-secondary btn-sm"
                  style={{ padding: '8px 12px' }}
                  onClick={() => {
                    const newKeys = [...config.keys]
                    newKeys.splice(idx, 1)
                    setConfig({ ...config, keys: newKeys })
                  }}
                >
                  Удалить
                </button>
              </div>
            ))}
            {config.keys.length === 0 && (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, fontStyle: 'italic', padding: 'var(--space-sm) 0' }}>
                Ключи не заданы. Будут использоваться дефолтные из системного .env
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (loading) return <div className="page-body">Загрузка настроек...</div>

  return (
    <>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Ключи интеграций (API)</h1>
          <p className="subtitle">Настройка пула ключей, ротации и моделей</p>
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Сохранение...' : '💾 Сохранить изменения'}
        </button>
      </div>

      <div className="page-body">
        <div style={{ maxWidth: 900, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
          
          <div className="card">
            <div className="card-header" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <span style={{ fontSize: 24 }}>🧠</span>
                <div>
                  <div className="card-title">Нейросети (LLM)</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Автоматическое переключение при лимитах (Quota Exceeded)</div>
                </div>
              </div>
            </div>

            {renderServiceSection('Google Gemini', 'Генерация Alt-тегов', gemini, setGemini, ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.0-pro-exp'])}
            <div style={{ borderBottom: '1px solid var(--border-color)', margin: 'var(--space-lg) 0' }}></div>
            {renderServiceSection('OpenAI (ChatGPT)', 'Генерация SEO-статей', openai, setOpenAI, ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'])}
            <div style={{ borderBottom: '1px solid var(--border-color)', margin: 'var(--space-lg) 0' }}></div>
            {renderServiceSection('Anthropic (Claude)', 'Альтернатива для генерации текстов', anthropic, setAnthropic, ['claude-3-5-sonnet-20240620', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'])}
          </div>

          <div className="card">
            <div className="card-header" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <span style={{ fontSize: 24 }}>📊</span>
                <div>
                  <div className="card-title">SEO Сервисы</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Доступы к SEO аналитике</div>
                </div>
              </div>
            </div>

            {renderServiceSection('Keys.so', 'Сбор маркерных запросов и поиск прямых конкурентов', keysSo, setKeysSo)}
            <div style={{ borderBottom: '1px solid var(--border-color)', margin: 'var(--space-lg) 0' }}></div>
            {renderServiceSection('SEMRush', 'Анализ ссылочной массы и бюджета', semrush, setSemrush)}
          </div>

          <div className="card">
            <div className="card-header" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <span style={{ fontSize: 24 }}>🕸️</span>
                <div>
                  <div className="card-title">Web & SERP Парсинг</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Анализ поисковой выдачи и сайтов</div>
                </div>
              </div>
            </div>

            {renderServiceSection('Perplexity', 'Глубокий анализ УТП конкурентов через Web Search', perplexity, setPerplexity, ['sonar-pro', 'sonar', 'llama-3.1-sonar-huge-128k-online'])}
            <div style={{ borderBottom: '1px solid var(--border-color)', margin: 'var(--space-lg) 0' }}></div>
            {renderServiceSection('Serper.dev', 'Съем позиций и проверка индексации ссылок', serper, setSerper)}
          </div>

        </div>
      </div>
    </>
  )
}
