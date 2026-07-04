FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Command is overridden in docker-compose.yml, but this is a good default
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
