# Contexto: la carpeta equipo3-cumplimiento-gcp
#   docker build -f services/evidence/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY services/evidence/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY comun ./comun
COPY services/evidence/evidence ./evidence
ENV PORT=8080 HOME=/tmp PYTHONUNBUFFERED=1
USER 65534
CMD ["python", "-m", "evidence"]
