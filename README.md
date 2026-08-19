# Investment Board（股票看板）

> 个人自托管、**只读**的股票看板：本地自选列表（增删）+ 实时行情 + 个股与全局新闻。
> 全部数据来自公开接口，无需任何账户登录。仅供个人学习研究，不构成投资建议。

## 功能

- **看板**：自选股票实时行情（价格 / 涨跌幅 / 迷你分时 sparkline）
- **自选**：本地自选列表管理页，支持**文件夹分类**（同花顺式：新建 / 重命名 / 删除 / 折叠展开），顶部统一输入 6 位代码按文件夹添加；预置「持仓 + 15 领域龙头」16 个文件夹 111 只股票，行情卡随自选实时联动
- **新闻**：全局快讯流 + 个股新闻（按自选列表自动筛选），支持已读标记
- **设置**：数据源健康状态（行情 / 新闻）

## 合规声明

- **仅供个人学习研究**，**不构成任何投资建议**。
- **数据版权**归新浪 / 腾讯 / 东方财富 / 财联社等各数据源所有；本项目不存储、再分发其数据。
- **纯公开数据源**：不接入任何需登录的第三方账户接口（无同花顺 / 券商账户查询）。
- **只读、无交易功能**：后端代码级限制——无任何下单 / 撤单 / 委托能力；
  CI 静态检查（`scripts/check_no_trade.py`）会拦截任何含交易语义的标识符，从代码层面保证只读。
- **访问频率受控**：行情 3s、新闻 60s（+ 随机抖动），不进行高频抓取。

完整合规说明见 [docs/compliance.md](docs/compliance.md)。

## 隐私说明

- **数据不出本机**：后端只绑定 `127.0.0.1`（端口 8210），无遥测、无上报、无第三方 SDK。
- **本地自选列表**：仅存于本机 `~/.investment-board/watchlist.json`（JSON 明文，含并发锁与原子写），
  可在「设置」页或直接删除该文件清除。
- **无需登录**：不存在任何账户凭据、会话令牌或加密密钥。

## 快速开始

前置：macOS / Linux，Python ≥ 3.11，Node ≥ 20。

```bash
# 1. 安装依赖
make install

# 2. 启动后端（终端 1）
make dev-backend

# 3. 启动前端（终端 2）
make dev-frontend
```

浏览器打开 <http://localhost:5173>（Vite 默认绑定 localhost，可能为 IPv6 `::1`，个别环境可用
`http://127.0.0.1:5173`）。在「自选」页输入 6 位股票代码（如 600519）即可添加并查看实时行情，
无需任何登录。

后端健康检查：

```bash
curl -s http://127.0.0.1:8210/api/status
# {"sources":{"market":"ok","news":"ok"}}
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
│   │   ├── core/              # 调度器（3s/60s 采集循环）+ 事件总线 + 本地自选存储
│   │   ├── market/            # 行情源适配器（新浪为主、腾讯为备）
│   │   ├── news/              # 新闻源适配器（东财公告 + 财联社电报）
│   │   └── models.py          # 数据模型
│   ├── tests/                 # pytest 测试（respx 模拟 HTTP，不依赖真实账号）
│   └── pyproject.toml
├── frontend/                  # React + Vite + ECharts（深色主题）
│   └── src/
│       ├── pages/             # 看板 / 自选 / 新闻 / 设置
│       ├── api/               # REST 客户端 + WebSocket（自动重连）
│       └── store.tsx          # zustand 状态
├── docs/                      # 架构 / 合规说明
├── scripts/check_no_trade.py  # 合规静态检查（禁止交易语义）
├── LICENSE
└── README.md
```

## 开发与验证

```bash
make check     # 合规静态检查（禁止交易语义标识符/中文词）
make lint      # ruff + yapf + eslint + prettier
make typecheck # mypy + tsc
make test      # 后端 pytest（23 个用例）
make build     # 前端 TypeScript 检查 + Vite 构建
```

CI（GitHub Actions）会自动执行以上检查。

## 常见问题（FAQ）

### 1. 新闻页没有数据？

全局快讯与个股公告依赖第三方公开接口（财联社电报 / 东财公告），**可能因第三方接口
变化或风控而暂时无数据**，后端会记录告警日志并优雅返回空列表（不会崩溃）。
这是外部数据源的预期行为，可稍后再试。

### 2. 行情不更新 / 显示异常？

行情来自新浪 / 腾讯的公开接口，同样可能因接口变化或风控而暂时无数据。后端会记录告警日志
并优雅降级（不崩溃）。可稍后再试；若持续异常，可查看后端日志（`cd backend && ./run.sh`）。

### 3. 如何反馈问题 / 贡献？

- 提交 Issue：说明复现步骤、后端日志（`cd backend && ./run.sh` 的告警输出）。
- 提交 PR：遵守只读约束（不得引入任何交易语义代码，需通过 `make check`），
  解析器改动需配套 `respx` 驱动的单元测试。

### 4. 自选列表存在哪里？如何清除？

自选列表存于 `~/.investment-board/watchlist.json`（JSON 明文，v2 分组结构：`{version, groups:[{name, stocks}]}`，v1 扁平列表自动迁移到「未分组」）。清除方式：
在「自选」页删除股票 / 删除整个文件夹（连带其中股票），或直接删除该文件（删除后按空列表处理，服务不崩溃）。

### 5. 换端口 / 换数据目录？

后端支持环境变量：`IB_PORT`（端口，默认 8210）、`IB_DATA_DIR`（数据目录，默认
`~/.investment-board/`）。前端代理目标固定为 `127.0.0.1:8210`（见 `frontend/vite.config.ts`）。
