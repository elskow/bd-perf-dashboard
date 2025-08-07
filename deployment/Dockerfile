# Multi-stage build for unified dashboard and backend deployment
FROM node:20-slim AS dashboard-build

# Install necessary dependencies for node-gyp and native modules
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Build the React Router dashboard
WORKDIR /app/dashboard
COPY dashboard/package*.json ./

# Clear npm cache and reinstall everything to fix Rollup issue
RUN npm cache clean --force
RUN rm -rf node_modules package-lock.json
RUN npm install

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

# Install curl for health checks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

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
