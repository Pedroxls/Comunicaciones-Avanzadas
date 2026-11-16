# Contexto: la carpeta equipo3-cumplimiento-gcp
#   docker build -f sensors/drift/Dockerfile .
# La imagen lleva las políticas y el Terraform del commit que se construyó:
# el drift se evalúa contra lo que está en main.
FROM python:3.12-slim
WORKDIR /app
COPY sensors/drift/requirements.txt sensors/drift/instalar_herramientas.py ./
RUN pip install --no-cache-dir -r requirements.txt && python instalar_herramientas.py /usr/local/bin
COPY comun ./comun
COPY sensors/drift/drift ./drift
COPY policies/rego ./policies/rego
COPY infra/modules ./infra/modules
COPY infra/environments ./infra/environments
# Deja los providers descargados; el backend se configura al correr.
RUN terraform -chdir=infra/environments/dev init -backend=false -input=false
ENV PORT=8080 MODO=servidor POLITICAS_DIR=/app/policies/rego INFRA_DIR=/app/infra/environments/dev PYTHONUNBUFFERED=1
CMD ["python", "-m", "drift"]
