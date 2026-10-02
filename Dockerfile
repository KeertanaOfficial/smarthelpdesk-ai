FROM python:3.10

WORKDIR /app

# Copy dependency list first so this layer caches independently of app code
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

# Copy the rest of the app (see .dockerignore for what's excluded —
# .env* files are NOT copied into the image; pass secrets with `docker run -e`)
COPY . .

RUN mkdir -p /app/data/chroma

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
