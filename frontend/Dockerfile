# ============================================
# XgenPCB Frontend - Production Dockerfile
# ============================================

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git

# Copy package files
COPY frontend/apps/web/package.json ./

# Install dependencies (no lockfile exists, use npm install with legacy peer deps)
RUN npm install --legacy-peer-deps

# Copy source
COPY frontend/apps/web/ ./

# Build the app
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine AS production

# Install curl for healthcheck
RUN apk add --no-cache curl

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY infra/nginx/nginx.conf /etc/nginx/nginx.conf
COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy built app from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create healthcheck endpoint
RUN echo '{"status":"healthy"}' > /usr/share/nginx/html/health

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
