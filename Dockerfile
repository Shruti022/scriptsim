FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/tools/ ./tools/
COPY backend/agents/ ./agents/
COPY backend/schemas/ ./schemas/
COPY backend/orchestrator.py .
COPY backend/api/ ./api/

EXPOSE 8080

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
