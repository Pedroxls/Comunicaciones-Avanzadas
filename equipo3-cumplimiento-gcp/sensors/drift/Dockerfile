FROM python:3.12-slim
WORKDIR /app
COPY drift ./drift
CMD ["python", "-c", "from drift.evaluar import hallazgos_desde_mensajes; print('drift listo')"]
