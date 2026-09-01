# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
# Install the project's runtime dependencies (declared in pyproject.toml)
# into the venv without requiring a full `pip install -e .` build step.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 1000 scribe
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY . .
RUN mkdir -p /app/data/audio && chown -R scribe:scribe /app

USER scribe

EXPOSE 8000

# Run pending migrations then start the API. In production, replace
# --reload with a process manager / multiple workers as needed.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
