FROM python:3.11-slim

# psycopg2 needs libpq; build tools removed after install to keep image small.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

# Run alembic migrations, then start uvicorn. If migrations fail, the
# container exits — we will not silently boot with a stale schema.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
