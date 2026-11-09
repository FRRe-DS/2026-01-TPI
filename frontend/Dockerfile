# Imagen del front de M2 Clientes (RNF-04): compila con Node y sirve los archivos estáticos con nginx.
#   docker build -t ghcr.io/frre-ds/m2-clientes-front:dev .
# Vite mete las URLs en el código al compilar: para otra API u otro Keycloak, pasarlas con --build-arg.

# --- Etapa 1: compilar
FROM node:22-slim AS build
WORKDIR /app

# Primero solo las dependencias, para reutilizar la capa si no cambian
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_URL=http://localhost:8000
ARG VITE_KEYCLOAK_URL=http://localhost:8080
ARG VITE_KEYCLOAK_REALM=ds-2026-realm
ARG VITE_KEYCLOAK_CLIENT_ID=m2-frontend
RUN npm run build

# --- Etapa 2: servir. La imagen final no lleva Node ni el código fuente, solo dist/
FROM nginx:1.28-alpine

LABEL org.opencontainers.image.title="M2 Clientes Front (Grupo 1)" \
      org.opencontainers.image.description="Front del cliente para M2 del TPI DS 2026, UTN FRRe" \
      org.opencontainers.image.source="https://github.com/FRRe-DS/2026-01-TPI"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1
