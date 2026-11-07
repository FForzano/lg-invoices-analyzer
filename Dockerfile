FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
ENV DATA_DIR=/data PATH="/srv/.venv/bin:$PATH" PYTHONUNBUFFERED=1
# utente non root (uid 1000, gid 100 "users" come nei compose tipici di OMV/Synology); sovrascrivibile con `user:`
RUN mkdir /data && chown 1000:100 /data
USER 1000:100
VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=5)"
# timeout alto: l'aggiornamento delle offerte scarica ~35 MB
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--workers", "2", "--timeout", "180", "--no-control-socket", "app:create_app()"]
