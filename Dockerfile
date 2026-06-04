FROM python:3.10

WORKDIR /app

# Copy everything
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

COPY .env.production /app/.env

# IMPORTANT: point to correct module path
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]