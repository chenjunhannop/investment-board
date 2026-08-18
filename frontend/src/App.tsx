import { useEffect } from 'react'
import { useApp } from './store'

export default function App() {
  const init = useApp((s) => s.init)
  useEffect(() => { init() }, [init])
  return <div className="app"><h1>Investment Board</h1></div>
}
