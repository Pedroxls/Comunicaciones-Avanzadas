# Contexto: la carpeta equipo3-cumplimiento-gcp
#   docker build -f agent/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY comun ./comun
COPY agent/cumplimiento ./cumplimiento
COPY policies/catalog ./catalogo
ENV PORT=8080 HOME=/tmp CATALOGO_DIR=/app/catalogo PYTHONUNBUFFERED=1
USER 65534
CMD ["python", "-m", "cumplimiento"]
