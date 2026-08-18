import { useEffect, useState } from 'react'
import { useApp } from './store'
import Dashboard from './pages/Dashboard'
import Positions from './pages/Positions'
import News from './pages/News'
import Settings from './pages/Settings'

type Page = 'dashboard' | 'positions' | 'news' | 'settings'

export default function App() {
  const init = useApp((s) => s.init)
  const [page, setPage] = useState<Page>('dashboard')
  useEffect(() => { init() }, [init])
  return (
    <div className="app">
      <header className="topbar">
        <h1>Investment Board</h1>
        <nav className="tabs">
          {([
            ['dashboard', '看板'],
            ['positions', '持仓'],
            ['news', '新闻'],
            ['settings', '设置'],
          ] as const).map(([key, label]) => (
            <button key={key} className={page === key ? 'active' : ''}
                    onClick={() => setPage(key)}>
              {label}
            </button>
          ))}
        </nav>
      </header>
      {page === 'dashboard' && <Dashboard />}
      {page === 'positions' && <Positions />}
      {page === 'news' && <News />}
      {page === 'settings' && <Settings />}
    </div>
  )
}
