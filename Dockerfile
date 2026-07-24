FROM python:3.12-slim AS builder

WORKDIR /app

# Cache Prisma partagé (query engine + CLI Node), chemin fixe et indépendant du HOME
ENV PRISMA_BINARY_CACHE_DIR=/opt/prisma-cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.txt

COPY prisma ./prisma
# Génère le client ET bake le query engine + la CLI Node dans le cache partagé
RUN prisma generate


FROM python:3.12-slim AS runtime

# stdout non bufferisé : sinon les logs de l'app restent coincés sous Swarm (pas de TTY)
ENV PYTHONUNBUFFERED=1
# Même chemin de cache qu'au build : Prisma trouve les binaires bakés au lieu de les réinstaller au runtime
ENV PRISMA_BINARY_CACHE_DIR=/opt/prisma-cache

RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libatomic1 libpq5  \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /opt/prisma-cache /opt/prisma-cache
COPY --from=builder /app/prisma ./prisma

COPY main.py init.py ./
COPY src ./src

# Le cache Prisma doit appartenir à appuser (c'est lui qui exécute connect() et migrate deploy)
RUN chown -R appuser:appuser /app /opt/prisma-cache

USER appuser

EXPOSE ${SERVER_PORT:-8095}

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:"${SERVER_PORT:-8095}"/health || exit 1

CMD ["sh", "-c", "\
  export DB_PASSWORD=$(cat /run/secrets/db_password) && \
  export DATABASE_URL=postgresql://auth:${DB_PASSWORD}@${DB_HOST:-auth-service_db}:5432/auth && \
  export DISCORD_CLIENT_ID=$(cat /run/secrets/discord_client_id) && \
  export DISCORD_CLIENT_SECRET=$(cat /run/secrets/discord_client_secret) && \
  export JWT_SECRET=$(cat /run/secrets/jwt_secret) && \
  until prisma migrate deploy; do echo 'DB pas prête, retry...'; sleep 2; done && \
  python main.py"]