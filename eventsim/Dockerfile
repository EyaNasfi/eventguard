FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY eventsim ./eventsim
RUN pip install --no-cache-dir . && useradd --create-home eventsim && mkdir /data && chown eventsim /data

USER eventsim
ENV EVENTSIM_DATABASE_URL=sqlite:////data/eventsim.db
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# One worker: the snapshot used by /_test/state-diff lives in process memory.
CMD ["uvicorn", "--factory", "eventsim.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
