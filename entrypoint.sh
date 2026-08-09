#!/usr/bin/env bash
# Konteyner har ishga tushganda bajariladi.
# Render'ning Docker runtime'ida build.sh ishlamaydi, shuning uchun
# migratsiyalar shu yerda ishga tushiriladi (migrate idempotent — takror
# ishlasa hech narsa buzilmaydi).

echo "==> Bazani kutmoqda..."
# Render Postgres birinchi so'rovda uyg'onishi mumkin — bir necha marta urinamiz.
MIGRATE_OK=0
for i in 1 2 3 4 5; do
  if python manage.py migrate --noinput; then
    echo "==> Migratsiyalar bajarildi."
    MIGRATE_OK=1
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

if [ "$MIGRATE_OK" = "1" ]; then
  # Admin hisobi. Render Free tarifida Shell yo'q, shuning uchun
  # ADMIN_PHONE / ADMIN_PASSWORD env'lari orqali yaratiladi.
  # Buyruq idempotent — hisob bor bo'lsa faqat parolni yangilaydi.
  python manage.py ensure_admin || echo "!!! ensure_admin bajarilmadi"

  # Demo ma'lumot (tumanlar, e'lonlar, test hisoblari).
  # Faqat SEED_DEMO=1 bo'lganda. Sinovdan keyin env'ni olib tashlang —
  # aks holda har deploy'da demo ma'lumot qayta yoziladi.
  if [ "$SEED_DEMO" = "1" ]; then
    echo "==> SEED_DEMO=1 — demo ma'lumot yaratilmoqda..."
    python manage.py seed_demo || echo "!!! seed_demo bajarilmadi"
  fi
fi

echo "==> Gunicorn ishga tushmoqda (port ${PORT})..."
exec gunicorn uyimiz.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers 2 \
  --threads 4 \
  --worker-class gthread \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
