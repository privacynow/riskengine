# Dockerfile for Decision Engine
FROM node:24-slim AS ui-build
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code only. Local secrets are excluded via .dockerignore
# (auth.tokens.local.json, .env.local) and mounted at runtime by Compose.
COPY . .
COPY --from=ui-build /ui/dist ./ui/dist

# Expose port 8000 for the FastAPI server
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
