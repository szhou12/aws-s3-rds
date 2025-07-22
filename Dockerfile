# Start from a minimal Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y gcc libmariadb-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements first and install (for better Docker cache)
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy rest of the project
COPY . /app/

# Expose port for FastAPI/Uvicorn
EXPOSE 8000

# Default command to run your app
CMD ["uvicorn", "app_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
