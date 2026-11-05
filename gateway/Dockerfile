FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY eventsim ./eventsim
COPY config ./config
COPY gateway ./gateway
RUN pip install --no-cache-dir ".[gateway]" && useradd --create-home gateway

USER gateway
EXPOSE 8100
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/health')"

CMD ["python", "-m", "gateway"]
