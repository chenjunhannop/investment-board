import { useCallback, useEffect, useRef, useState } from 'react'
import { logout, pollLogin, startLogin } from '../api/client'
import { useApp } from '../store'

export default function Settings() {
  const status = useApp((s) => s.status)
  const refresh = useApp((s) => s.refresh)
  const [qr, setQr] = useState<string>('')
  const [scanning, setScanning] = useState(false)
  const timer = useRef<number>()

  const beginLogin = useCallback(async () => {
    const r = await startLogin()
    setQr(r.qrcode_data)
    setScanning(true)
    timer.current = window.setInterval(async () => {
      const r = await pollLogin()
      if (r.ok) {
        window.clearInterval(timer.current)
        setScanning(false)
        setQr('')
        await refresh()
      }
    }, 2000)
  }, [refresh])

  const doLogout = useCallback(async () => {
    await logout()
    await refresh()
  }, [refresh])

  useEffect(() => () => { if (timer.current) window.clearInterval(timer.current) }, [])

  return (
    <div className="page">
      <h2>设置</h2>
      <section className="panel">
        <h3>同花顺账号（只读）</h3>
        {status?.logged_in ? (
          <>
            <p>已登录。程序仅读取自选与持仓，不做任何交易操作。</p>
            <button className="danger" onClick={doLogout}>注销并清除全部本地数据</button>
          </>
        ) : (
          <>
            <button onClick={beginLogin}>使用同花顺 App 扫码登录</button>
            {qr && (
              <div className="qr-box">
                <p className="muted">请在手机同花顺 App 扫描下方二维码：</p>
                <pre className="qr-code">{qr}</pre>
                <p className="muted">（MVP：二维码以文本形式展示，可全选复制；图形渲染为收尾扩展点）</p>
              </div>
            )}
            {scanning && <p className="muted">等待扫码确认…</p>}
          </>
        )}
      </section>
      <section className="panel">
        <h3>数据源健康</h3>
        <ul>
          <li>同花顺接口：{status?.logged_in ? '🟢 已连接' : '⚪ 未登录'}</li>
          <li>行情源：{status?.sources?.market ?? '—'}</li>
          <li>新闻源：{status?.sources?.news ?? '—'}</li>
        </ul>
        <p className="muted">行情来源：新浪财经 / 腾讯财经（公开接口）；新闻来源：东方财富公告 / 财联社电报</p>
      </section>
    </div>
  )
}
