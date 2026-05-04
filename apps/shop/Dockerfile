FROM python:3.10-slim

WORKDIR /app

# The apps rely on flask and possibly other common dependencies.
# Assuming standard flask app.
RUN pip install flask requests

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
