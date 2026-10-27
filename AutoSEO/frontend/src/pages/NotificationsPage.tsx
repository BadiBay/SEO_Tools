import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filterUnread, setFilterUnread] = useState(false)

  useEffect(() => {
    loadNotifications()
  }, [filterUnread])

  const loadNotifications = async () => {
    try {
      setLoading(true)
      const data = await api.getNotifications({ unread_only: filterUnread })
      setNotifications(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const markAsRead = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await api.markNotificationRead(id)
      // Update local state
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
    } catch (err) {
      console.error(err)
    }
  }

  if (loading && notifications.length === 0) return <div className="page-body">Загрузка уведомлений...</div>

  return (
    <>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Уведомления</h1>
          <p className="subtitle">События проектов и результаты проверок</p>
        </div>
        
        <div style={{ display: 'flex', gap: 8 }}>
          <button 
            className={`btn ${!filterUnread ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilterUnread(false)}
          >
            Все
          </button>
          <button 
            className={`btn ${filterUnread ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilterUnread(true)}
          >
            Непрочитанные
          </button>
        </div>
      </div>

      <div className="page-body">
        <div className="card" style={{ padding: 0 }}>
          {notifications.length === 0 ? (
            <div style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-muted)' }}>
              Уведомлений нет
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {notifications.map(notif => (
                <Link 
                  to={notif.project_id ? `/project/${notif.project_id}` : '#'} 
                  key={notif.id}
                  style={{
                    padding: 'var(--space-md)',
                    borderBottom: '1px solid var(--border-color)',
                    display: 'flex',
                    gap: 'var(--space-md)',
                    background: notif.is_read ? 'transparent' : 'var(--bg-secondary)',
                    textDecoration: 'none',
                    color: 'inherit',
                    transition: 'background 0.2s',
                    alignItems: 'flex-start'
                  }}
                  className="hover-bg-light"
                >
                  <div style={{ 
                    fontSize: 24, 
                    marginTop: 4,
                    color: notif.severity === 'critical' || notif.severity === 'warning' ? 'var(--danger)' : 'var(--primary)'
                  }}>
                    {notif.event_type === 'link_dead' ? '🔗' : 
                     notif.event_type === 'pipeline_completed' ? '✅' :
                     notif.event_type === 'pipeline_failed' ? '❌' : '🔔'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <strong style={{ 
                        color: notif.severity === 'critical' ? 'var(--danger)' : 
                               notif.severity === 'warning' ? '#f59e0b' : 'inherit'
                      }}>{notif.title}</strong>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {new Date(notif.created_at).toLocaleString('ru-RU')}
                      </span>
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 8 }}>
                      {notif.message}
                    </div>
                    {!notif.is_read && (
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '4px 8px', fontSize: 12 }}
                        onClick={(e) => markAsRead(notif.id, e)}
                      >
                        Отметить прочитанным
                      </button>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
