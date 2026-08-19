# README 更新与 Docker 部署设计文档

- 日期：2026-08-18
- 状态：设计已获用户认可（Part 1-2）
- 目标：按阿里写作规范重写 README（配图 + 使用 + 部署），新增本地生产运行与 Docker 单容器部署

## 1. 目标

1. **README 按阿里规范重写**（`/tmp/f2e-spec/docs/engineering/writing.md`：中英文之间空格、中英文与数字之间空格、半角标点后空格、全角标点不加空格、清晰分节）
2. **配图**：功能截图（大屏主页 + 自选页），存 `docs/screenshots/`
3. **使用方法**：安装 / 启动 / 添加自选 / 功能说明
4. **部署方法**：
   - 本地生产运行（后端 uvicorn 托管前端 dist，单端口 8210）
   - Docker 单容器部署（docker-compose 一键）

## 2. 非目标（明确不做）

- 不做多容器 nginx 部署（用户选 A：单容器，后端托管静态）
- 不改现有功能、API、数据源
- 不引入 HTTPS/公网暴露（保持本地 127.0.0.1 隐私定位）
- 不新增 CI 部署流程

## 3. 部署架构（单容器）

### 3.1 本地生产运行
```
frontend: npm ci && npm run build → frontend/dist/
backend:  uvicorn app.main（托管 frontend/dist 静态文件）
访问:     http://127.0.0.1:8210（单端口，前端 API /api 同源）
```

### 3.2 Docker 单容器（多阶段 Dockerfile）
```
Stage 1 (node:20-alpine): npm ci && npm run build → 前端 dist
Stage 2 (python:3.11-slim): pip 装后端依赖 + COPY dist → uvicorn app.main
docker-compose.yml: 端口 127.0.0.1:8210:8210（仅本地访问，隐私保持）
```

### 3.3 后端改动（让单容器可行）
- `backend/app/main.py`：新增静态文件托管
  - `/api`、`/ws` 路由优先
  - 其余路径服务 `frontend/dist` 静态文件（`StaticFiles(html=True)`）
  - SPA fallback：未知路径返回 `index.html`（前端单页应用）
- `backend/app/config.py`：新增 `IB_HOST` 环境变量（`settings.host` 可被覆盖；Docker 容器内需 `0.0.0.0`，宿主机映射 `127.0.0.1:8210` 保持隐私）
- 静态目录路径：优先环境变量 `IB_DIST_DIR`（Docker 内指向镜像内 dist），默认 `frontend/dist`（本地）

## 4. 配图

- `docs/screenshots/dashboard.png`：大屏主页（headless Chrome 截 `localhost:5173`，1920×1080）
- `docs/screenshots/watchlist.png`：自选页（文件夹分类）
- README 顶部功能预览引用

## 5. README 结构（阿里规范）

```markdown
# Investment Board（股票看板）

> 简介：个人自托管、只读的股票看板……（阿里中英文空格规范）

## 功能预览
![大屏](docs/screenshots/dashboard.png)
![自选](docs/screenshots/watchlist.png)

## 功能特性
- 看板大屏 / 自选文件夹 / 新闻 / 设置

## 快速开始（使用）
- 前置：macOS/Linux、Python ≥ 3.11、Node ≥ 20
- make install / make dev-backend / make dev-frontend
- 浏览器访问 5173，添加自选代码

## 部署
### 本地生产运行
npm run build + uvicorn（单端口 8210）
### Docker 部署
docker compose up -d（单容器，127.0.0.1:8210）

## 技术架构
后端 FastAPI + 前端 React/Vite + 数据源（新浪/腾讯/东财）

## 目录结构
backend/ frontend/ docs/ scripts/ Makefile

## 数据源与合规
纯公开数据源 / 只读 / 版权声明

## 隐私
本地 127.0.0.1 / 无遥测 / 数据不出本机

## 常见问题（FAQ）
新闻/行情数据源变动 / 端口修改

## 贡献 / License
```

## 6. 约束与合规

- **只读红线**：不得引入 buy/sell/trade/order 前缀标识符或中文交易业务词；`make check` 必须 OK
- **工具链**：ruff/yapf/mypy/eslint/prettier 全绿；`make test` 保持 31 passed；`make build` 成功
- Docker 文件（Dockerfile/docker-compose.yml）不含交易语义
- 后端静态托管不改变现有 API 契约；`/api/status`、`/api/quotes`、`/api/news` 等保持
- 命令：`backend/.venv/bin/`；前端 `cd frontend && npm run ...`
- README 遵循阿里写作规范（中英文空格等）；commit 用 `docs:`（README）/ `feat:`（部署支持）

## 7. 验收标准

1. `make check/lint/typecheck/test/build` 全绿（31 passed）
2. **本地生产**：`npm run build` 后后端托管 dist，访问 `http://127.0.0.1:8210` 打开大屏（非 dev 代理）
3. **Docker**：`docker compose up -d` 后 `http://127.0.0.1:8210` 正常（大屏 + 自选 + 新闻全功能）
4. README 按阿里规范（中英文空格、分节清晰），含 2 张截图、使用与部署章节
5. `docs/screenshots/*.png` 存在且 README 可引用

## 8. 参考

- 阿里写作规范：`/tmp/f2e-spec/docs/engineering/writing.md`（中英文空格、标点规约）
- 现有：`README.md`（126 行）、`Makefile`、`backend/app/main.py`（无静态托管）、`frontend/vite.config.ts`（仅 dev 代理）、前端 API 相对路径（同源兼容）
