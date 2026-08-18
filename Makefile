# Makefile
.PHONY: install test build check lint typecheck format dev-backend dev-frontend

install:
	cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]" respx
	cd frontend && npm install

test:
	cd backend && .venv/bin/pytest -q

build:
	cd frontend && npm run build

check:
	python3 scripts/check_no_trade.py

# 代码规范闸门
lint:  ## 双端 lint + 格式检查
	@echo "== backend: ruff =="
	@cd backend && .venv/bin/ruff check app tests
	@echo "== backend: yapf =="
	@cd backend && .venv/bin/yapf -dr app tests
	@echo "== frontend: eslint =="
	@cd frontend && npm run lint
	@echo "== frontend: prettier =="
	@cd frontend && npm run format:check

typecheck:  ## 双端类型检查
	@cd backend && .venv/bin/mypy app
	@cd frontend && npx tsc -b

format:  ## 全量格式化（后端 yapf + 前端 prettier）
	@cd backend && .venv/bin/yapf -ri app tests
	@cd frontend && npm run format

dev-backend:
	cd backend && ./run.sh

dev-frontend:
	cd frontend && npm run dev
