# ---------- Build stage ----------
FROM python:3.14.0b2-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

COPY . .

# ---------- Final stage ----------
FROM python:3.14.0b2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --gid 1001 --system app && \
    adduser --no-create-home --shell /bin/false --disabled-password --uid 1001 --system --ingroup app app

COPY --from=builder /install /usr/local 
COPY --from=builder /app /app

RUN install -d -o app -g app /app/logs

USER app

CMD ["python", "main.py"]
