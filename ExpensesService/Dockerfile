FROM python:3.11-slim


WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Systemabh�ngigkeiten f�r Pillow und Build-Tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Anwendungscode (app/ Ordner direkt in /app/)
COPY app/ ./

# .env.example als Vorlage hinterlegen (keine echten Secrets ins Image!)
COPY .env.example .env.example

# EntryPoint
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "web:app"]
