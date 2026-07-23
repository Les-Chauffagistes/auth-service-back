FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY prisma ./prisma
RUN prisma generate


FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libatomic1 libpq5  \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/prisma-python /root/.cache/prisma-python
COPY --from=builder /app/prisma ./prisma

COPY . .

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