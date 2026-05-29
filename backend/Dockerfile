FROM python:3.11-slim

# psycopg2 needs libpq; postgresql-client provides pg_dump for the nightly
# backup Celery task. Both layers cleaned up after install to keep image
# small. Debian-stable ships postgresql-client 15; pg_dump 15 → server 16
# is forward-compatible per Postgres versioning policy.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

# Migrations are run by the entry command of the backend service ONLY (see docker-compose.yml + railway.json). Worker and beat reuse this image and MUST NOT run alembic — they share the schema written by the backend service.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
