# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.10.2 AS uv
FROM python:3.15-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9 AS dependencies
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra aws --no-install-project

FROM dependencies AS embeddings
ENV HF_HUB_DISABLE_XET=1
RUN /app/.venv/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/opt/models')" && chmod -R a+rX /opt/models

FROM python:3.15-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9 AS local
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    RUNBOOKOPS_ROOT=/app RUNBOOKOPS_DATA=/app/.state RUNBOOKOPS_MODE=offline RUNBOOKOPS_EMBEDDING=hash
COPY --from=dependencies /app/.venv /app/.venv
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
COPY resources ./resources
COPY scripts/mcp_entry.py ./scripts/mcp_entry.py
RUN uv pip install --no-deps --python /app/.venv/bin/python . && \
    useradd --uid 1000 --create-home runbookops && mkdir /app/.state && chown 1000:1000 /app/.state
USER 1000:1000
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]
CMD ["uvicorn", "runbookops.api:app_factory", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]

FROM local AS agentcore
ENV RUNBOOKOPS_DATA=/tmp/runbookops RUNBOOKOPS_MODEL_CACHE=/opt/models HF_HUB_DISABLE_XET=1
COPY --from=embeddings /opt/models /opt/models
EXPOSE 8080
HEALTHCHECK NONE
CMD ["uvicorn", "runbookops.api:app_factory", "--host", "0.0.0.0", "--port", "8080", "--no-proxy-headers"]
