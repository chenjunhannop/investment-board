import { useState } from 'react';
import PriceCard from '../components/PriceCard';
import { useApp } from '../store';

export default function Watchlist() {
  const quotes = useApp((s) => s.quotes);
  const watchlist = useApp((s) => s.watchlist);
  const addGroup = useApp((s) => s.addGroup);
  const renameGroup = useApp((s) => s.renameGroup);
  const removeGroup = useApp((s) => s.removeGroup);
  const addToWatchlist = useApp((s) => s.addToWatchlist);
  const removeFromWatchlist = useApp((s) => s.removeFromWatchlist);
  const [code, setCode] = useState('');
  const [group, setGroup] = useState('');
  const [newGroup, setNewGroup] = useState('');
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const submit = async () => {
    if (!/^\d{6}$/.test(code.trim()) || !group) return;
    await addToWatchlist(group, code.trim());
    setCode('');
  };

  const handleRename = async (name: string) => {
    // 计划指定用 window.prompt 简化重命名
    // eslint-disable-next-line no-alert
    const newName = window.prompt(`重命名「${name}」`, name);
    if (newName && newName.trim() && newName.trim() !== name) {
      await renameGroup(name, newName.trim());
    }
  };

  const handleRemove = async (name: string) => {
    // 计划指定用 window.confirm 确认删除
    // eslint-disable-next-line no-alert
    if (window.confirm(`确认删除文件夹「${name}」及其中的全部股票？`)) {
      await removeGroup(name);
    }
  };

  return (
    <div className="page">
      <h2>自选</h2>
      <div className="watchlist-toolbar">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="输入 6 位股票代码"
          maxLength={6}
        />
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">选择文件夹</option>
          {watchlist.groups.map((g) => (
            <option key={g.name} value={g.name}>
              {g.name}
            </option>
          ))}
        </select>
        <button onClick={submit}>添加</button>
        <input
          value={newGroup}
          onChange={(e) => setNewGroup(e.target.value)}
          placeholder="新建文件夹名"
        />
        <button
          onClick={async () => {
            await addGroup(newGroup.trim());
            setNewGroup('');
          }}
        >
          新建文件夹
        </button>
      </div>
      {watchlist.groups.map((g) => (
        <section key={g.name} className="group">
          <div
            className="group-header"
            onClick={() => setCollapsed((c) => ({ ...c, [g.name]: !c[g.name] }))}
          >
            <span className="group-arrow">{collapsed[g.name] ? '▸' : '▾'}</span>
            <span className="group-name">{g.name}</span>
            <span className="group-count">({g.stocks.length})</span>
            <span className="group-actions">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRename(g.name);
                }}
              >
                重命名
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemove(g.name);
                }}
              >
                删除
              </button>
            </span>
          </div>
          {!collapsed[g.name] && (
            <div className="grid">
              {g.stocks.map((w) => {
                const q = quotes[w.code];
                if (!q) return null;
                return (
                  <div key={w.code} className="cell">
                    <PriceCard q={q} />
                    <button className="remove" onClick={() => removeFromWatchlist(g.name, w.code)}>
                      删除
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      ))}
      {watchlist.groups.length === 0 && <div className="muted">暂无自选文件夹</div>}
    </div>
  );
}
