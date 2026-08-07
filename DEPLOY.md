# Uyimiz.uz backend — Fly.io ga deploy

Loyiha deploy'ga tayyorlangan: Postgres, Tigris (S3) media, WhiteNoise static,
gunicorn, Docker. Quyidagi qadamlarni ketma-ket bajaring.

---

## 0. Tayyorgarlik (bir marta)

```bash
# flyctl o'rnatish (Windows PowerShell)
iwr https://fly.io/install.ps1 -useb | iex

fly auth signup     # yoki: fly auth login
```

Fly.io kredit karta so'raydi (verifikatsiya uchun). Kichik app ~$0-5/oy.

---

## 1. App yaratish

Loyiha papkasida:

```bash
fly launch --no-deploy
```

- `Dockerfile` va `fly.toml` allaqachon bor — Fly ularni ishlatadi.
- App nomini so'raydi (masalan `uyimiz-backend`). Nom band bo'lsa boshqasini tanlang
  va `fly.toml` dagi `app = "..."` ni ham yangilang.
- Region: **fra** (Frankfurt) yoki **cdg** — O'zbekistonga eng yaqinlari.
- "Would you like to set up a Postgres database?" → **Yes** desangiz keyingi qadamni
  o'tkazib yuborasiz.

---

## 2. Postgres ulash

```bash
fly postgres create --name uyimiz-db --region fra
fly postgres attach uyimiz-db --app uyimiz-backend
```

`attach` avtomatik `DATABASE_URL` secret'ini qo'shadi — qo'lda yozish shart emas.

> Muqobil: Supabase yoki Neon (bepul tier bor). U holda ularning connection
> string'ini `DATABASE_URL` qilib bering va `DJANGO_DB_SSL=1` qiling.

---

## 3. Media uchun Tigris bucket

Rasm va shartnoma PDF'lari deploy'da yo'qolmasligi uchun object storage kerak:

```bash
fly storage create --name uyimiz-media
```

Bu avtomatik `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_ENDPOINT_URL_S3`, `BUCKET_NAME` secret'larini qo'shadi.
Faqat bittasini qo'lda moslash kerak:

```bash
fly secrets set AWS_STORAGE_BUCKET_NAME=$(fly storage list | grep uyimiz-media | awk '{print $1}')
# yoki Fly bergan bucket nomini ko'chirib yozing:
# fly secrets set AWS_STORAGE_BUCKET_NAME=uyimiz-media-xxxx
```

---

## 4. Secret'larni o'rnatish

```bash
# Kalit generatsiya (lokalda):
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

```bash
fly secrets set \
  DJANGO_SECRET_KEY="yuqorida-chiqqan-kalit" \
  DJANGO_ALLOWED_HOSTS="uyimiz-backend.fly.dev" \
  DJANGO_CSRF_TRUSTED_ORIGINS="https://uyimiz-backend.fly.dev" \
  CORS_ALLOW_ALL="0" \
  CORS_ALLOWED_ORIGINS="https://uyimiz.uz,https://admin.uyimiz.uz"
```

> Mobil ilova (native) uchun CORS kerak emas — faqat brauzerdagi frontend uchun.
> Frontend hali tayyor bo'lmasa vaqtincha `CORS_ALLOW_ALL=1` qo'ying,
> lekin prod'da albatta `0` ga qaytaring.

Barcha o'zgaruvchilar ro'yxati — `.env.example` faylida.

---

## 5. Deploy

```bash
fly deploy
```

Nima bo'ladi:
1. Docker image build bo'ladi, `collectstatic` build vaqtida ishlaydi.
2. `release_command` → `python manage.py migrate --noinput` avtomatik bajariladi.
3. Gunicorn 8080-portda ko'tariladi, `/api/health` health-check bilan tekshiriladi.

Tekshirish:

```bash
curl https://uyimiz-backend.fly.dev/api/health
# {"status": "ok", "service": "uyimiz-backend"}
```

---

## 6. Superuser va boshlang'ich ma'lumot

```bash
fly ssh console -C "python manage.py createsuperuser"
```

Interaktiv ishlamasa:

```bash
fly ssh console
cd /app && python manage.py createsuperuser
```

Demo/seed ma'lumot bo'lsa (core ilovasida):

```bash
fly ssh console -C "python manage.py seed_demo"   # buyruq nomi loyihangizga qarab
```

---

## 7. Foydali buyruqlar

```bash
fly logs                    # jonli loglar
fly status                  # machine holati
fly ssh console             # serverga kirish
fly secrets list            # secret'lar (qiymatlari ko'rinmaydi)
fly scale memory 1024       # RAM oshirish
fly scale count 2           # instance qo'shish
fly postgres connect -a uyimiz-db   # bazaga psql orqali
```

---

## 8. Domen ulash (ixtiyoriy)

```bash
fly certs add api.uyimiz.uz
fly certs show api.uyimiz.uz     # qanday DNS yozuv kerakligini ko'rsatadi
```

Keyin secret'larga domenni qo'shing:

```bash
fly secrets set \
  DJANGO_ALLOWED_HOSTS="uyimiz-backend.fly.dev,api.uyimiz.uz" \
  DJANGO_CSRF_TRUSTED_ORIGINS="https://uyimiz-backend.fly.dev,https://api.uyimiz.uz"
```

---

## Nima o'zgardi (deploy tayyorgarligi)

| Fayl | O'zgarish |
|---|---|
| `requirements.txt` | gunicorn, whitenoise, psycopg, dj-database-url, django-storages, boto3 |
| `uyimiz/settings.py` | `DATABASE_URL` orqali Postgres; S3/Tigris media; WhiteNoise static; HSTS/SSL/secure cookies; env'dan CORS va ALLOWED_HOSTS; console logging |
| `uyimiz/urls.py` | media serve endi `DEBUG` ga emas, `USE_S3` ga bog'liq |
| `Dockerfile` | Python 3.12-slim, build-time collectstatic, non-root user, gunicorn |
| `.dockerignore` | db.sqlite3, media, .env, .git image'ga tushmaydi |
| `fly.toml` | port 8080, health check, `release_command` = migrate |
| `.env.example` | barcha env o'zgaruvchilar namunasi |

Lokalda hech narsa buzilmadi — `DATABASE_URL` va `AWS_STORAGE_BUCKET_NAME`
bo'lmasa loyiha eski holicha sqlite + lokal media bilan ishlayveradi.

---

## Deploy'dan keyin qilinadigan ishlar

Muhimlik tartibida:

**1. Ma'lumotlarni ko'chirish (agar sqlite'da kerakli data bo'lsa)**

```bash
# lokalda
python manage.py dumpdata --natural-foreign --natural-primary \
  -e contenttypes -e auth.Permission -e sessions > data.json
# serverga
fly ssh sftp shell        # put data.json /app/data.json
fly ssh console -C "python manage.py loaddata /app/data.json"
```

**2. DRF ruxsatlarini qattiqlashtirish** — hozir
`DEFAULT_PERMISSION_CLASSES = ['AllowAny']`. Prod uchun `IsAuthenticated` ni
default qilib, ochiq endpoint'larga (e'lonlar ro'yxati, health, OTP) view
darajasida `AllowAny` qo'yish xavfsizroq.

**3. Token o'rniga JWT** — hozir DRF `TokenAuthentication`, token muddatsiz.
`djangorestframework-simplejwt` refresh/expiry beradi.

**4. SMS provayder** — OTP hozir konsolga chiqadimi yoki real yuboriladimi
tekshiring. Eskiz.uz yoki Play Mobile integratsiyasi kerak bo'ladi.

**5. Rate limiting** — OTP va login endpoint'lariga DRF throttling
(`DEFAULT_THROTTLE_RATES`) qo'ying, aks holda SMS spam qilinadi.

**6. Sentry** — xatolarni kuzatish uchun `sentry-sdk[django]`. Bepul tier yetarli.

**7. Backup** — Fly Postgres avtomatik snapshot oladi, lekin
`fly postgres backup list` bilan tekshirib turing va haftalik dump'ni
tashqariga saqlang.

**8. Background job'lar** — PDF generatsiya (reportlab) hozir request ichida.
Sekinlashsa Celery + Redis yoki oddiyroq `django-q2` ga o'tkazing.

**9. CI/CD** — GitHub Actions bilan `main` ga push bo'lganda avtomatik deploy:
`FLY_API_TOKEN` secret'i (`fly tokens create deploy`) + `superfly/flyctl-actions`.

**10. `db.sqlite3` ni git'dan olib tashlang** — `.gitignore` da bor, lekin
avval commit qilingan bo'lsa tarixda qoladi:
`git rm --cached db.sqlite3`
