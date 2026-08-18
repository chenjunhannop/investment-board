# Makefile
.PHONY: install test build check dev-backend dev-frontend

install:
	cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]" respx
	cd frontend && npm install

test:
	cd backend && .venv/bin/pytest -q

build:
	cd frontend && npm run build

check:
	python3 scripts/check_no_trade.py

dev-backend:
	cd backend && ./run.sh

dev-frontend:
	cd frontend && npm run dev
