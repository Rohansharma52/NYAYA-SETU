# NYAYA SETU — single-container build (React UI + FastAPI API on one URL).
# Used for free cloud hosting (Render). Demo data is re-seeded on every start.

# 1) Build the React frontend
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npx vite build

# 2) Python API that also serves the built UI
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/static \
    DATABASE_URL=sqlite:///./nyaya_setu.db \
    APP_ENV=production
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist ./static
EXPOSE 8000
CMD ["sh", "-c", "python seed.py --reset && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
