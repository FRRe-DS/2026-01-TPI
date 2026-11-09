# Imagen de la API de M2 Clientes (RNF-04). Formato OCI estándar.
#   docker build -t ghcr.io/frre-ds/m2-clientes-api:dev .
# La configuración entra por variables de entorno (RNF-06, ver config.py): el .env no se copia.
FROM python:3.13-slim

LABEL org.opencontainers.image.title="M2 Clientes API (Grupo 1)" \
      org.opencontainers.image.description="API de clientes (M2) de la plataforma de movilidad del TPI DS 2026, UTN FRRe" \
      org.opencontainers.image.source="https://github.com/FRRe-DS/2026-01-TPI"

# Sin archivos .pyc y con los logs al instante (sin buffer)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero solo las dependencias: si no cambian, Docker reutiliza esta capa y el build es mucho más rápido
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No corre como root: si alguien vulnera la API, no tiene permisos de administrador en el contenedor
RUN useradd --create-home --uid 10001 m2
USER m2

EXPOSE 8000

# Docker marca el contenedor como "unhealthy" si /health no responde 200 (por ejemplo, si se cae MongoDB)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
