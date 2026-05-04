FROM python:3.10-slim

WORKDIR /app

RUN pip install flask requests

COPY . .

EXPOSE 5002

CMD ["python", "app.py"]
