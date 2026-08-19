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
