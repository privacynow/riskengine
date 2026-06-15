# Dockerfile for the Risk Engine
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app, including the ui directory
COPY . .

# Expose port 8000 for the FastAPI server
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

