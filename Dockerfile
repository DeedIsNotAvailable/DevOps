FROM python:3.13-bookworm AS base
WORKDIR /app

FROM base AS python-deps
COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM base AS browser
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium \
    && rm -rf /var/lib/apt/lists/*

FROM python-deps AS tools
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY src/ ./src/
ENTRYPOINT ["python", "src/cloud_cli.py"]

FROM browser AS runtime
COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY src/ ./src/
CMD ["python", "src/worker.py"]
