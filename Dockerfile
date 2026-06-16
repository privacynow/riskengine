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

# Runtime whitelist only — no Node toolchain, source tree, or host node_modules.
COPY *.py ./
COPY routes/ ./routes/
COPY services/ ./services/
COPY demo/ ./demo/
COPY sql/ ./sql/
# Tests support CI/local `docker compose exec risk-engine pytest`; not a minimal prod image.
COPY tests/ ./tests/
COPY pytest.ini ./
COPY README.md ./
COPY --from=ui-build /ui/dist ./ui/dist

# Expose port 8000 for the FastAPI server
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
