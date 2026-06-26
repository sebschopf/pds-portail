# Stage 1: build — compile les dependances avec uv
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Installe uv (package manager rapide)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copie les fichiers de dependances et le code source
COPY pyproject.toml uv.lock ./
COPY app/ ./app/

# Installe les dependances sans outils dev, puis nettoie le cache uv
RUN uv sync --frozen --no-dev && uv cache clean

# Stage 2: run — image minimale pour la production (PDS-55)
FROM python:3.12-slim AS run

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/tmp/.uv-cache

# Cree un utilisateur non-root pour la securite avec uid/gid 999
# (correspond aux permissions du volume monte par Fly.io)
RUN groupadd --system --gid 999 appgroup && useradd --system --no-create-home --uid 999 --gid appgroup appuser

WORKDIR /app

# Copie uv depuis le stage build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copie les fichiers necessaires depuis le stage build
COPY --from=build /build/pyproject.toml /build/uv.lock ./
COPY --from=build /build/.venv ./.venv
COPY --from=build /build/app/ ./app/

# Volume persistant pour le cache SQLite (monte par fly.toml)
RUN mkdir -p /var/data && chown appuser:appgroup /var/data

# Donne les droits d'ecriture a appuser sur /app pour eviter
# "Permission denied" lors du build editable de setuptools par uv run
RUN chown -R appuser:appgroup /app

# HEALTHCHECK Docker pour permettre a Fly.io de detecter une instance malade
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD uv run python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health')" || exit 1

# Bascule vers l'utilisateur non-root
USER appuser

# Demarre uvicorn via uv run python -m (evite le shebang casse du binaire uvicorn)
CMD ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
