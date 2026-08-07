#!/usr/bin/env bash
# Konteyner har ishga tushganda bajariladi.
# Render'ning Docker runtime'ida build.sh ishlamaydi, shuning uchun
# migratsiyalar shu yerda ishga tushiriladi (migrate idempotent — takror
# ishlasa hech narsa buzilmaydi).
set -o errexit

echo "==> Migratsiyalar..."
python manage.py migrate --noinput

echo "==> Gunicorn ishga tushmoqda (port ${PORT})..."
exec gunicorn uyimiz.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers 2 \
  --threads 4 \
  --worker-class gthread \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
