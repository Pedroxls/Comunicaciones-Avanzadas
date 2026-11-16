# Contexto: la carpeta equipo3-cumplimiento-gcp
#   docker build -f services/freno/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY services/freno/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY comun ./comun
COPY services/freno/freno ./freno
ENV PORT=8080 HOME=/tmp PYTHONUNBUFFERED=1
USER 65534
CMD ["python", "-m", "freno"]
