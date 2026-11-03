# Helm dashboard as a container, for AWS App Runner / ECS Fargate / Elastic Beanstalk.
# Runs in demo mode with no secrets; set env vars on the service to go live.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEMO_MODE=1 \
    PORT=8080

# Dependencies first, so the layer caches across code changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# App Runner health check hits this; the app warms its cache at startup.
EXPOSE 8080
CMD ["sh", "-c", "uvicorn ui.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
