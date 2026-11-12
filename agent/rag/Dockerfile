FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY config ./config
COPY agent ./agent
COPY procedures ./procedures
RUN pip install --no-cache-dir ".[agent]" && useradd --create-home retriever

USER retriever
EXPOSE 8200
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8200/health')"

CMD ["uvicorn", "--factory", "agent.rag.service:create_app", "--host", "0.0.0.0", "--port", "8200", "--workers", "1"]
