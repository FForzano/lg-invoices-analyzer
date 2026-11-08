# 1) front-end React (Vite): si compila qui, nell'immagine finale resta solo il risultato statico
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

# 2) app Flask + front-end compilato
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY --from=frontend /build/dist ./frontend/dist
ENV DATA_DIR=/data FRONTEND_DIR=/srv/frontend/dist PATH="/srv/.venv/bin:$PATH" PYTHONUNBUFFERED=1
# utente non root (uid 1000, gid 100 "users" come nei compose tipici di OMV/Synology); sovrascrivibile con `user:`
RUN mkdir /data && chown 1000:100 /data
USER 1000:100
VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=5)"
# timeout alto: l'aggiornamento delle offerte scarica ~35 MB
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--workers", "2", "--timeout", "180", "--no-control-socket", "app:create_app()"]
