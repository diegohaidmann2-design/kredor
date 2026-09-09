# JuroFácil Frontend - Multi-stage Build

# ==================== Stage 1: Build ====================
FROM node:18-alpine AS builder

WORKDIR /app

# Chromium para o prerender estático (SEO). puppeteer-core usa este binário.
RUN apk add --no-cache chromium nss freetype freetype-dev harfbuzz ca-certificates ttf-freefont
ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Copiar package files
COPY package.json yarn.lock* package-lock.json* ./

# Instalar dependências
RUN if [ -f yarn.lock ]; then \
        yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
        npm ci; \
    else \
        npm install --legacy-peer-deps && npm install ajv ajv-keywords --save-dev --legacy-peer-deps; \
    fi

# Copiar código fonte
COPY . .

# Otimizações para VPS com pouca RAM
ENV GENERATE_SOURCEMAP=false
ENV NODE_OPTIONS="--max-old-space-size=2048"

# Build da aplicação
ENV NODE_OPTIONS="--max-old-space-size=2048"
RUN if [ -f yarn.lock ]; then \
        yarn build; \
    else \
        npm run build; \
    fi

# ==================== Stage 2: Production ====================
FROM nginx:1.25-alpine

LABEL maintainer="JuroFácil"
LABEL description="Frontend React para Sistema de Gestão de Empréstimos"

# Remover config padrão do nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copiar build do React
COPY --from=builder /app/build /usr/share/nginx/html

# Copiar configuração do nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Criar script para injetar variáveis de ambiente no runtime
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expor porta
EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/ || exit 1

# Entrypoint customizado para injetar env vars
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
