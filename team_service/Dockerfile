FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "team_service.wsgi:application", "-b", "0.0.0.0:8002", "--workers", "3"]
