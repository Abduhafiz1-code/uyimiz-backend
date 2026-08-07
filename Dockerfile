# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Eslatma: Render'da "Python" runtime ishlatiladi (render.yaml + build.sh).
# Bu Dockerfile lokal test va zaxira variant (Render Docker runtime) uchun.

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

# Pillow va reportlab uchun kerakli kutubxonalar
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libfreetype6-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# collectstatic build vaqtida (baza kerak emas)
RUN DJANGO_DEBUG=0 \
    DJANGO_SECRET_KEY=build-only-dummy-key \
    DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

RUN chmod +x /app/entrypoint.sh

# root bo'lmagan foydalanuvchi
RUN useradd -m -u 1000 uyimiz && chown -R uyimiz:uyimiz /app
USER uyimiz

EXPOSE 10000

# entrypoint: migrate → gunicorn. $PORT ni Render avtomatik beradi.
CMD ["/app/entrypoint.sh"]
