FROM python:3.10-slim

WORKDIR /app

RUN pip install flask requests

COPY . .

EXPOSE 5001

CMD ["python", "app.py"]
