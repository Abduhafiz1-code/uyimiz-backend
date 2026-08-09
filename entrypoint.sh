#!/usr/bin/env bash
# Konteyner har ishga tushganda bajariladi.
# Render'ning Docker runtime'ida build.sh ishlamaydi, shuning uchun
# migratsiyalar shu yerda ishga tushiriladi (migrate idempotent — takror
# ishlasa hech narsa buzilmaydi).

echo "==> Bazani kutmoqda..."
# Render Postgres birinchi so'rovda uyg'onishi mumkin — bir necha marta urinamiz.
for i in 1 2 3 4 5; do
  if python manage.py migrate --noinput; then
    echo "==> Migratsiyalar bajarildi."
    break
  fi
  if [ "$i" = "5" ]; then
    echo "!!! DIQQAT: migratsiya bajarilmadi (5 urinishdan keyin)."
    echo "!!! Server baribir ishga tushiriladi — sababni bilish uchun"
    echo "!!! /api/health manzilini oching."
  else
    echo "    urinish $i muvaffaqiyatsiz, 5 soniyadan keyin qayta..."
    sleep 5
  fi
done

echo "==> Gunicorn ishga tushmoqda (port ${PORT})..."
exec gunicorn uyimiz.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers 2 \
  --threads 4 \
  --worker-class gthread \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
