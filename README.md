# Investment Board（股票看板）

> 个人自托管、**只读**的股票看板：自选实时行情、持仓盈亏、个股与全局新闻。
> 仅供个人学习研究，不构成投资建议。

## 功能

- **看板**：自选股票实时行情（价格 / 涨跌幅 / 迷你分时 sparkline）+ 持仓盈亏汇总卡片
- **持仓**：明细表（成本 / 现价 / 市值 / 浮动盈亏 / 当日盈亏）
- **新闻**：全局快讯流（公开源，未登录也可看）+ 个股新闻（按自选 / 持仓自动筛选），支持已读标记
- **设置**：同花顺 App 扫码登录（只读）、注销并一键清除本地数据、数据源健康状态

## 合规声明

- **仅供个人学习研究**，**不构成任何投资建议**。
- **数据版权**归同花顺 / 新浪 / 腾讯 / 东方财富 / 财联社等各数据源所有；本项目不存储、再分发其数据。
- **账号风险自担**：接入第三方账户查询接口可能违反其服务条款，请自行确认后使用。
- **只读、无交易功能**：后端代码级限制——`ths_client` 仅有登录 / 查询方法，无任何下单 / 撤单 / 委托能力；
  CI 静态检查（`scripts/check_no_trade.py`）会拦截任何含交易语义的标识符，从代码层面保证只读。
- **访问频率受控**：行情 3s、持仓 10s、新闻 60s（+ 随机抖动），不进行高频抓取。

完整合规说明见 [docs/compliance.md](docs/compliance.md)。

## 隐私说明

- **凭据仅存本机加密**：会话令牌用 AES-256-GCM 加密后写入本机 `~/.investment-board/session.enc`，
  加密密钥存系统 Keychain（macOS / Windows / Linux Secret Service），密钥永不进代码、永不落盘明文。
- **数据不出本机**：后端只绑定 `127.0.0.1`（端口 8210），无遥测、无上报、无第三方 SDK。
- **一键清除**：设置页「注销并清除全部本地数据」会删除会话、清空缓存并移除加密记录。

## 快速开始

前置：macOS / Linux（Windows 需自行适配 Keychain），Python ≥ 3.11，Node ≥ 20。

```bash
# 1. 安装依赖
make install

# 2. 启动后端（终端 1）
make dev-backend

# 3. 启动前端（终端 2）
make dev-frontend
```

浏览器打开 <http://localhost:5173>（Vite 默认绑定 localhost，可能为 IPv6 `::1`，个别环境可用
`http://127.0.0.1:5173`），进入「设置」页用同花顺 App 扫码登录即可看到自选与持仓；
不登录也能看到全局快讯与「看板」的深色主题页面（行情 / 持仓为空）。

后端健康检查：

```bash
curl -s http://127.0.0.1:8210/api/status
# {"logged_in":false,"sources":{"market":"ok","news":"ok"},"ths":{"status":"not_logged_in"}}
```

## 架构

总览与模块职责见 [docs/architecture.md](docs/architecture.md)（含 Mermaid 架构图与数据流）。

## 目录结构

```
investment-board/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口（lifespan 组装采集器与调度器）
│   │   ├── api/               # REST（/api/*）+ WebSocket（/ws）
│   │   ├── core/              # 调度器（3s/10s/60s 采集循环）+ 事件总线
│   │   ├── ths_client/        # 同花顺网页版只读客户端（扫码登录/自选/持仓）
│   │   ├── market/            # 行情源适配器（新浪为主、腾讯为备）
│   │   ├── news/              # 新闻源适配器（东财公告 + 财联社电报）
│   │   ├── vault/             # 凭据保险箱（AES-256-GCM + Keychain）
│   │   └── models.py          # 数据模型
│   ├── tests/                 # pytest 测试（respx 模拟 HTTP，不依赖真实账号）
│   └── pyproject.toml
├── frontend/                  # React + Vite + ECharts（深色主题）
│   └── src/
│       ├── pages/             # 看板 / 持仓 / 新闻 / 设置
│       ├── api/               # REST 客户端 + WebSocket（自动重连）
│       └── store.tsx          # zustand 状态
├── docs/                      # 架构 / 合规 / 逆向接口说明
├── scripts/check_no_trade.py  # 合规静态检查（禁止交易语义）
├── LICENSE
└── README.md
```

## 开发与验证

```bash
make check   # 合规静态检查（禁止交易语义标识符/中文词）
make test    # 后端 pytest（29 个用例）
make build   # 前端 TypeScript 检查 + Vite 构建
```

CI（GitHub Actions）会自动执行以上三项。

## 常见问题（FAQ）

### 1. 同花顺（THS）接口失效怎么办？

第三方接口可能随时变化。后端已做**分层降级**：THS 失效时行情 / 新闻照常运行，
界面会提示「自选 / 持仓暂不可用」，健康灯变为异常；登录态会通过 `refresh_session` 保活，
失效后提示重新扫码。

接口契约与抓包方法见 [docs/ths-reverse-engineering.md](docs/ths-reverse-engineering.md)。
如你抓包确认了新字段 / 新路径，欢迎提交 PR（指引见该文档）。

### 2. 新闻页没有数据？

全局快讯与个股公告依赖第三方公开接口（财联社电报 / 东财公告），**可能因第三方接口
变化或风控而暂时无数据**，后端会记录告警日志并优雅返回空列表（不会崩溃）。
这是外部数据源的预期行为，与登录状态无关。可稍后再试，或按第 1 条指引抓包核对接口。

### 3. 如何反馈问题 / 贡献？

- 提交 Issue：说明复现步骤、后端日志（`cd backend && ./run.sh` 的告警输出）。
- 提交 PR：遵守只读约束（不得引入任何交易语义代码，需通过 `make check`），
  解析器改动需配套 `respx` 驱动的单元测试。

### 4. 数据存在哪里？如何彻底清除？

- 加密会话：`~/.investment-board/session.enc`（AES-256-GCM 加密，密钥在系统 Keychain）。
- 彻底清除：设置页「注销并清除全部本地数据」，或手动删除该文件并删除 Keychain 中
  `investment-board` 条目。

### 5. 换端口 / 换数据目录？

后端支持环境变量：`IB_PORT`（端口）、`IB_DATA_DIR`（数据目录）、
`IB_THS_ENDPOINT`（同花顺接口前缀，默认 `https://eq.10jqka.com.cn`）。前端代理目标固定为
`127.0.0.1:8210`（见 `frontend/vite.config.ts`）。
