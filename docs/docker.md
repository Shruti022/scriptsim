---
paths:
- "Dockerfile"
- "requirements.txt"
- "docker-compose.yml"
---
# Docker Rules

## Base image (never change this)
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
This image already has Chromium installed. Do not install it manually.

## Chromium launch flags (required inside Docker)
Always use these args when launching Playwright:
args=["--no-sandbox", "--disable-dev-shm-usage"]

## Cloud Run constraints
- Container must start HTTP server on port 8080
- Use FastAPI + uvicorn for the HTTP server
- CMD should be: ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]

## GCP authentication inside container
Use Application Default Credentials — do not hardcode keys.
Cloud Run service account handles auth automatically.
