# README 更新与 Docker 部署实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按阿里写作规范重写 README（配图 + 使用 + 部署），新增本地生产运行（后端 uvicorn 托管前端 dist）与 Docker 单容器部署（docker-compose 一键，单端口 127.0.0.1:8210）。

**Architecture:** 后端 FastAPI 挂载 `frontend/dist` 静态文件（`/api`、`/ws` 路由优先，其余走静态）；新增 `IB_HOST`（Docker 容器内 0.0.0.0）与 `IB_DIST_DIR`（dist 路径）环境变量；多阶段 Dockerfile（node 构建前端 → python 运行后端）+ docker-compose（端口映射 127.0.0.1:8210）；headless Chrome 截图存 `docs/screenshots/`；README 按阿里写作规范重写。

**Tech Stack:** FastAPI/uvicorn（Python 3.11）、React/Vite（Node 20）、Docker/compose、headless Chrome

## Global Constraints

- 只改：`backend/app/{main,config}.py`、`backend/tests/*`（如需）、新建 `Dockerfile`、`docker-compose.yml`、`.dockerignore`、`docs/screenshots/*.png`、`README.md`、`docs/superpowers/plans/...`
- **只读红线**：不得引入 buy/sell/trade/order 前缀标识符或中文交易业务词；`python3 scripts/check_no_trade.py` 必须 OK；Docker 文件也遵守
- **工具链**：`make check/lint/typecheck/test/build` 全绿（test 31 passed）；前端 `cd frontend && npm run ...`
- 后端静态托管**不改 API 契约**：`/api/status`、`/api/quotes`、`/api/news`、`/api/watchlist`、`/ws` 保持
- 前端 API 已是相对路径（`fetch('/api/...')`）→ 生产同源，无需改前端
- 隐私保持：docker-compose 端口映射 `127.0.0.1:8210:8210`（仅本地访问）
- Docker 容器内 `IB_HOST=0.0.0.0`、`IB_DIST_DIR=/app/frontend/dist`、`IB_DATA_DIR=/data`
- README 遵循阿里写作规范（中英文之间空格、中英文与数字之间空格、半角标点后空格、全角标点不加空格、列表/标题层级清晰）
- commit 用 `feat:`（部署支持）/ `docs:`（README/截图）
- 命令：`backend/.venv/bin/`；Docker 用 `docker compose`（v2）

---

### Task 1: 后端静态托管 + 环境变量

**Files:**
- Modify: `backend/app/config.py`（`IB_HOST`、`IB_DIST_DIR`）
- Modify: `backend/app/main.py`（挂载静态文件）

**Interfaces:**
- Consumes: `settings.host/port/dist_dir`
- Produces: 生产单端口服务（`/api`、`/ws` 优先，其余走 dist 静态）

- [ ] **Step 1: config.py 新增 dist_dir 与 IB_HOST**

```python
    host: str = "127.0.0.1"
    port: int = 8210
    data_dir: Path = Path.home() / ".investment-board"
    dist_dir: Path = Path("frontend/dist")  # 前端构建产物目录
    quotes_interval: float = 3.0
    news_interval: float = 60.0
```

环境变量读取段追加：

```python
settings.host = os.environ.get("IB_HOST", settings.host)
settings.dist_dir = Path(os.environ.get("IB_DIST_DIR", str(settings.dist_dir)))
```

（`IB_PORT`/`IB_DATA_DIR` 已存在，保留。）

- [ ] **Step 2: main.py 挂载静态文件**

在 `app.include_router(ws_router)` 之后、`main()` 之前追加：

```python
from fastapi.staticfiles import StaticFiles

# 生产模式：托管前端构建产物（/api、/ws 路由优先，其余走静态）
if settings.dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(settings.dist_dir), html=True), name="static")
```

`main()` 不变（`uvicorn.run(..., host=settings.host, ...)` 已用 settings.host，Docker 内 `IB_HOST=0.0.0.0` 生效）。

> 说明：FastAPI 按注册顺序匹配，`/api`/`/ws` 路由先注册，`mount("/")` 最后匹配 → API 优先，静态兜底；`html=True` 使 `/` 返回 index.html（前端为单页无路由跳转，无需额外 SPA fallback）。

- [ ] **Step 3: 验证**

```bash
backend/.venv/bin/pytest -q   # 31 passed
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/mypy backend/app
python3 scripts/check_no_trade.py
```

- [ ] **Step 4: 本地生产冒烟（后端托管 dist）**

```bash
cd frontend && npm run build
cd backend && IB_DIST_DIR=/Users/chenjunhan/dev/project/investment-board/frontend/dist ./run.sh
# （上一条在前台跑后端；另开终端或后台方式执行下列检查）
sleep 5
curl -s http://127.0.0.1:8210/api/status   # API 正常
curl -s http://127.0.0.1:8210/ | grep -o "<title>[^<]*"   # index.html 正常
curl -s http://127.0.0.1:8210/assets/ | head -c 100   # 静态资源可访问
pkill -f "uvicorn app.main"
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/config.py backend/app/main.py
git commit -m "feat: 后端托管前端构建产物（生产单端口）+ IB_HOST/IB_DIST_DIR 配置"
```

---

### Task 2: Dockerfile + docker-compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

**Interfaces:**
- Consumes: Task 1（后端静态托管 + IB_HOST/IB_DIST_DIR）
- Produces: `docker compose up -d` → `http://127.0.0.1:8210`

- [ ] **Step 1: 创建 Dockerfile（多阶段）**

```dockerfile
# Stage 1: 构建前端
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: 后端 + 托管 dist
FROM python:3.11-slim
WORKDIR /app
COPY backend/pyproject.toml backend/
COPY backend/ backend/
RUN cd backend && pip install --no-cache-dir -e .
COPY --from=frontend /app/frontend/dist /app/frontend/dist
ENV IB_HOST=0.0.0.0 \
    IB_DIST_DIR=/app/frontend/dist \
    IB_DATA_DIR=/data
EXPOSE 8210
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8210"]
```

- [ ] **Step 2: 创建 docker-compose.yml**

```yaml
services:
  investment-board:
    build: .
    container_name: investment-board
    ports:
      - "127.0.0.1:8210:8210"  # 仅本地访问，隐私保持
    volumes:
      - investment-data:/data
    restart: unless-stopped

volumes:
  investment-data:
```

- [ ] **Step 3: 创建 .dockerignore**

```gitignore
.git
**/__pycache__
**/.venv
**/.pytest_cache
**/.mypy_cache
**/.ruff_cache
frontend/node_modules
frontend/dist
docs
node_modules
```

> 注意：`.dockerignore` 排除 `frontend/dist` 等，Docker 内 stage1 重新构建；排除 docs/node_modules 减小构建上下文。

- [ ] **Step 4: Docker 构建 + 启动实测**

```bash
docker compose build
docker compose up -d
sleep 8
curl -s http://127.0.0.1:8210/api/status       # API 正常（容器内）
curl -s http://127.0.0.1:8210/ | grep -o "<title>[^<]*"   # index.html
docker compose logs --tail 5 investment-board   # 无错误
docker compose down
```

- [ ] **Step 5: 提交**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: Docker 单容器部署（后端托管前端 + compose 一键）"
```

---

### Task 3: 功能截图

**Files:**
- Create: `docs/screenshots/dashboard.png`、`docs/screenshots/watchlist.png`

**Interfaces:**
- Consumes: 运行中的 dev 服务
- Produces: README 可引用的功能截图

- [ ] **Step 1: 启动 dev 服务并截图**

```bash
cd backend && (./run.sh &) && cd ../frontend && (npm run dev &)
sleep 8
# 用 headless Chrome（CDP）截大屏主页（等待指数/K线加载完成）
# 参考脚本：headless Chrome --headless=new --window-size=1920,1080 --screenshot=docs/screenshots/dashboard.png http://localhost:5173
# 自选页：先点击"自选" tab 再截图 → docs/screenshots/watchlist.png
pkill -f "uvicorn app.main"; pkill -f vite
```

> 实现时用 headless Chrome + CDP 等待数据渲染后截图（大屏：指数卡/K线出现；自选页：16 文件夹渲染）。

- [ ] **Step 2: 验证截图**

```bash
ls -la docs/screenshots/*.png   # 两个文件非空
file docs/screenshots/*.png     # PNG 格式
```

- [ ] **Step 3: 提交**

```bash
git add docs/screenshots/
git commit -m "docs: 新增功能截图（大屏 + 自选页）"
```

---

### Task 4: README 重写（阿里规范）

**Files:**
- Modify: `README.md`（完全重写）

**Interfaces:**
- Consumes: Task 3 截图、Task 1-2 部署支持
- Produces: 阿里规范 README（含使用 + 部署 + 配图）

- [ ] **Step 1: 重写 README.md**

按 spec §5 结构与阿里写作规范（中英文空格等）重写。要点：

- **简介**：一行定位（个人自托管、只读、纯公开数据源）
- **功能预览**：`![大屏](docs/screenshots/dashboard.png)` + `![自选](docs/screenshots/watchlist.png)`
- **功能特性**：大屏（7 模块）/ 自选文件夹 / 新闻 / 设置
- **快速开始**：前置（macOS/Linux、Python ≥ 3.11、Node ≥ 20）+ `make install` + `make dev-backend`/`make dev-frontend` + 访问 5173 + 添加自选
- **部署**：
  - 本地生产：`cd frontend && npm ci && npm run build` + `cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8210`（或 `make` 对应目标）+ 访问 `http://127.0.0.1:8210`
  - Docker：`docker compose up -d` + 访问 `http://127.0.0.1:8210`；`docker compose down` 停止
- **技术架构**：后端 FastAPI + 前端 React/Vite + 数据源（新浪/腾讯/东财公开接口）+ 事件总线/WS
- **目录结构**：backend/ frontend/ docs/ scripts/ Makefile
- **数据源与合规**：纯公开数据源、只读、版权声明、访问频率
- **隐私**：本地 127.0.0.1、无遥测、数据不出本机、Docker 端口仅映射 localhost
- **常见问题**：行情/新闻数据源变动（外部接口可能暂时无数据）、端口修改（IB_PORT/IB_HOST）、清除自选数据
- **贡献 / License**：只读红线（make check）、提交规范（约定式提交）

阿里写作规范检查：中英文之间空格（如 "Python 3.11"、"macOS / Linux"）、中英文与数字之间空格、半角标点后空格、全角标点不加空格、列表编号规范。

- [ ] **Step 2: 验证规范**

```bash
# 检查中英文间是否缺空格（抽查 + markdownlint 若有）
grep -nE "[a-zA-Z][中英文]|[0-9][中英文]" README.md | head   # 抽查中英混排
```

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: 按阿里写作规范重写 README（配图/使用/部署）"
```

---

### Task 5: 全量验收与推送

**Files:**
- Modify: `docs/superpowers/plans/2026-08-18-readme-docker-deploy-plan.md`（As-Built）

- [ ] **Step 1: 全量验收**

```bash
make check && make lint && make typecheck && make test && make build
```

Expected: 全绿（test 31 passed）。

- [ ] **Step 2: 端到端验证**

1. **本地生产**：`cd frontend && npm run build` + 后端跑（IB_DIST_DIR 默认 `frontend/dist`）+ `curl http://127.0.0.1:8210/` 返回 index.html + `/api/status` 正常
2. **Docker**：`docker compose build && docker compose up -d` + `curl http://127.0.0.1:8210/api/status` + 首页 + `docker compose down`
3. 浏览器打开 `http://127.0.0.1:8210`（生产单端口）确认大屏/自选/新闻功能完整

- [ ] **Step 3: As-Built + 推送**

计划文档末尾追加 As-Built 表（Task 1-4 commit hash、验证结果、偏差清单——含：静态托管用 `mount("/")` + `html=True`（前端无路由跳转无需 SPA fallback）、docker-compose 端口仅 localhost、`IB_HOST` 容器内 0.0.0.0、.dockerignore 排除 dist 由 stage1 重建）。然后：

```bash
git add docs/superpowers/plans/2026-08-18-readme-docker-deploy-plan.md
git commit -m "docs: README 与 Docker 部署计划追加执行记录（as-built）"
git push origin main
```

- [ ] **Step 4: 最终确认**

```bash
git status --short && git log --oneline origin/main..HEAD
```

Expected: 工作区干净、无未推送 commit。
