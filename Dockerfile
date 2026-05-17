# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Final image ───────────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="speedtest-monitor"
LABEL description="Network speed monitor — pure Python, no external binary required."

COPY --from=builder /install /usr/local

WORKDIR /app
COPY speedTest.py .
COPY speed_engine.py .
COPY graph_generator.py .

ENV DATA_DIR=/data
ENV INTERVAL_MINUTES=5

RUN mkdir -p /data
VOLUME ["/data"]

# -u = unbuffered so logs appear immediately in `docker logs`
CMD ["python", "-u", "speedTest.py"]