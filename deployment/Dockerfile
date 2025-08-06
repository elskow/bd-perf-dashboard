FROM node:20-alpine AS dashboard-build

WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm ci

COPY dashboard/ ./
RUN npm run build

FROM python:3.11-slim AS backend-build

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -r pyproject.toml

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -r pyproject.toml

COPY connector/ ./connector/
COPY scripts/ ./scripts/

COPY --from=dashboard-build /app/dashboard/build /var/www/html

COPY deployment/nginx.conf /etc/nginx/sites-available/default

COPY deployment/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN mkdir -p /var/log/supervisor /var/log/nginx /var/log/uvicorn

# Expose ports
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start supervisor to manage all services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
