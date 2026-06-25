FROM python:3.12-slim

# Evite les fichiers .pyc et le buffering stdout (logs visibles dans fly logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Repertoire de l'application
WORKDIR /app

# Installer uv (package manager rapide)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copier les fichiers de dependances ET le code (necessaire pour le build du package local)
COPY pyproject.toml uv.lock ./
COPY app/ ./app/

# Installer les dependances sans l'outil de dev
# Le package local pds-portail-backend sera installe en mode editable
RUN uv sync --frozen --no-dev

# Volume persistant pour le cache SQLite (monte par fly.toml)
RUN mkdir -p /var/data

# Demarrer uvicorn
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]