FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install docling --no-deps

FROM python:3.11-slim

RUN useradd --create-home --shell /bin/sh app

WORKDIR /app

COPY --from=builder /root/.local /home/app/.local
COPY --chown=app:app . .

RUN mkdir -p data && chown -R app:app /app /home/app/.local
USER app

ENV PATH=/home/app/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 