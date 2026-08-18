import { useCallback, useEffect, useRef, useState } from 'react';
import { logout, pollLogin, startLogin } from '../api/client';
import { useApp } from '../store';

export default function Settings() {
  const status = useApp((s) => s.status);
  const refresh = useApp((s) => s.refresh);
  const [qr, setQr] = useState<string>('');
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string>('');
  const [statusText, setStatusText] = useState<string>('');
  const timer = useRef<number>();

  const beginLogin = useCallback(async () => {
    setError('');
    setQr('');
    try {
      const r = await startLogin();
      if (!r.qrcode_img || r.error) {
        setError(r.error || '获取二维码失败，请稍后再试');
        return;
      }
      setQr(`data:image/png;base64,${r.qrcode_img}`);
      setScanning(true);
      setStatusText('请在手机同花顺 App 扫描二维码');
      timer.current = window.setInterval(async () => {
        const res = await pollLogin(r.qrid);
        if (res.ok) {
          window.clearInterval(timer.current);
          setScanning(false);
          setQr('');
          await refresh();
        } else if (res.reason === 'expired') {
          window.clearInterval(timer.current);
          beginLogin(); // 二维码失效自动刷新
        } else if (res.reason === 'confirmed') {
          setStatusText('已扫码，请在手机上确认登录');
        }
      }, 2000);
    } catch {
      setError('获取登录二维码失败，请检查后端服务后重试');
    }
  }, [refresh]);

  const doLogout = useCallback(async () => {
    await logout();
    await refresh();
  }, [refresh]);

  useEffect(
    () => () => {
      if (timer.current) window.clearInterval(timer.current);
    },
    [],
  );

  return (
    <div className="page">
      <h2>设置</h2>
      <section className="panel">
        <h3>同花顺账号（只读）</h3>
        {status?.logged_in ? (
          <>
            <p>已登录。程序仅读取自选与持仓，不做任何交易操作。</p>
            <button className="danger" onClick={doLogout}>
              注销并清除全部本地数据
            </button>
          </>
        ) : (
          <>
            <button onClick={beginLogin}>使用同花顺 App 扫码登录</button>
            {error && (
              <p className="muted" style={{ color: 'var(--up)' }}>
                {error}
              </p>
            )}
            {qr && (
              <div className="qr-box">
                <p className="muted">请在手机同花顺 App 扫描下方二维码：</p>
                <img
                  src={qr}
                  alt="同花顺登录二维码"
                  style={{
                    display: 'block',
                    width: 220,
                    height: 220,
                    borderRadius: 8,
                    marginTop: 8,
                  }}
                />
              </div>
            )}
            {scanning && <p className="muted">{statusText}</p>}
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
        <p className="muted">
          行情来源：新浪财经 / 腾讯财经（公开接口）；新闻来源：东方财富公告 / 财联社电报
        </p>
      </section>
    </div>
  );
}
