FROM python:3.12-slim

WORKDIR /code

# System deps: build-essential + libpq-dev are needed to build/link psycopg
# against libpq; curl is handy for debugging/healthchecks from inside the container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies before copying app code, so editing app code doesn't
# bust the (much slower) pip-install layer cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ml ./ml
COPY rag ./rag

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
