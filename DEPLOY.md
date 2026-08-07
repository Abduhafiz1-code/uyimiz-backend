# Uyimiz.uz backend — Render'ga deploy

Loyiha tayyorlangan: Postgres, S3-mos media storage, WhiteNoise static,
gunicorn, `render.yaml` blueprint.

- **URL:** https://uyimiz-backend.onrender.com
- **Service ID:** `srv-d9qsduijobas738m9fig`
- **Outbound IP'lar:** `74.220.50.0/24`, `74.220.58.0/24`
  (tashqi baza yoki SMS provayder firewall'iga shu diapazonlarni qo'shasiz)

---

## Holat: servis yaratilgan, sozlash qoldi

Servis allaqachon deploy bo'lgan, lekin hozircha **bazasi yo'q** —
env o'zgaruvchilar kiritilmagan bo'lsa konteyner ichidagi vaqtinchalik
sqlite'ga yozadi va har qayta ishga tushganda hamma narsa o'chadi.
Quyidagi 3 qadam shuni to'g'irlaydi.

---

## 1. Kodni GitHub'ga yuborish

Render GitHub'dan deploy qiladi, shuning uchun avval push:

```bash
git update-index --chmod=+x entrypoint.sh build.sh
git add .
git commit -m "Render: entrypoint bilan migrate, postgres, s3 media"
git push origin main
```

> `entrypoint.sh` ijro huquqiga ega bo'lishi **shart** — aks holda
> konteyner "permission denied" bilan ishga tushmaydi. Yuqoridagi
> `git update-index --chmod=+x` shuni hal qiladi (Windows'da chmod yo'q).

---

## 2. Postgres yaratish

Dashboard → **New** → **Postgres**

| Maydon | Qiymat |
|---|---|
| Name | `uyimiz-db` |
| Database | `uyimiz` |
| Region | **Frankfurt** (web service bilan bir xil bo'lishi shart) |
| Plan | Basic-256mb (~$6/oy) yoki Free (30 kun) |

Yaratilgach → **Info** bo'limidan **Internal Database URL** ni ko'chiring.

> ⚠️ **Internal** URL'ni oling, External'ni emas. Internal tezroq, bepul
> va SSL talab qilmaydi. External faqat tashqaridan (lokal kompyuteringizdan)
> ulanish uchun.

---

## 3. Environment o'zgaruvchilar

Servis → **Environment** → quyidagilarni qo'shing:

```
DATABASE_URL              = <Internal Database URL>
DJANGO_SECRET_KEY         = <pastdagi buyruq bilan yarating>
DJANGO_DEBUG              = 0
DJANGO_DB_SSL             = 0
DJANGO_ALLOWED_HOSTS      = uyimiz-backend.onrender.com
DJANGO_CSRF_TRUSTED_ORIGINS = https://uyimiz-backend.onrender.com
DJANGO_LOG_LEVEL          = INFO
CORS_ALLOW_ALL            = 0
CORS_ALLOWED_ORIGINS      = https://uyimiz.uz,https://admin.uyimiz.uz
PYTHON_VERSION            = 3.12.7
```

Kalit yaratish (lokalda):

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> Frontend hali tayyor bo'lmasa vaqtincha `CORS_ALLOW_ALL=1` qo'ying,
> prod'da albatta `0` ga qaytaring. Mobil ilova (native) uchun CORS kerak emas.

---

## 4. Runtime: Docker

Servis **Docker** runtime'da yaratilgan (Render repo'dagi `Dockerfile` ni
o'zi topgan). Bu holda Build/Start Command maydonlari **bo'sh qoladi** —
hammasi `Dockerfile` ichida:

```
Dockerfile  →  pip install + collectstatic  (build vaqtida)
            →  CMD entrypoint.sh            (konteyner ishga tushganda)
                  ├── python manage.py migrate --noinput
                  └── gunicorn ... --bind 0.0.0.0:$PORT
```

> ⚠️ **Muhim:** Docker runtime'da `build.sh` **ishlamaydi** — u faqat
> Render'ning "Python" runtime'i uchun. Shuning uchun migratsiyalar
> `entrypoint.sh` ga ko'chirildi. `migrate` idempotent, ya'ni har ishga
> tushganda takror bajarilishi xavfsiz.

Settings → **Health Check Path** = `/api/health` ekanini tekshiring.

---

## 5. Media storage (rasm va shartnoma PDF'lari)

Render diski efemer — deploy'da yuklangan fayllar **yo'qoladi**.
Shuning uchun S3-mos storage kerak. Bepul variantlar:

| Provayder | Bepul hajm | Endpoint |
|---|---|---|
| **Cloudflare R2** | 10 GB | `https://<account_id>.r2.cloudflarestorage.com` |
| **Tigris** | 5 GB | `https://t3.storage.dev` |
| **Backblaze B2** | 10 GB | `https://s3.<region>.backblazeb2.com` |

Bucket yaratib, access key olgach Environment'ga qo'shing:

```
AWS_STORAGE_BUCKET_NAME = uyimiz-media
AWS_ACCESS_KEY_ID       = ...
AWS_SECRET_ACCESS_KEY   = ...
AWS_ENDPOINT_URL_S3     = https://...
AWS_REGION              = auto
```

Bucket'ni **public read** qiling (rasmlar brauzerda ochilishi uchun) —
kod `AWS_QUERYSTRING_AUTH = False` bilan imzosiz URL beradi.

> Bu o'zgaruvchilar berilmasa loyiha lokal diskka yozadi va ishlayveradi,
> lekin har deploy'da fayllar o'chadi. Prod'da albatta sozlang.

---

## 6. Deploy va tekshirish

**Manual Deploy** → **Deploy latest commit**. Loglarda `Live` chiqqach:

```bash
curl https://uyimiz-backend.onrender.com/api/health
# {"status": "ok", "service": "uyimiz-backend"}
```

Admin panel: https://uyimiz-backend.onrender.com/admin/

---

## 7. Superuser yaratish

Servis → **Shell** tab (Starter plan va yuqorisida):

```bash
python manage.py createsuperuser
```

Free plan'da Shell yo'q — bir martalik buyruqni `build.sh` oxiriga
vaqtincha qo'shib, keyin olib tashlang:

```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
U = get_user_model()
U.objects.filter(phone='+998901234567').exists() or U.objects.create_superuser(phone='+998901234567', password='vaqtinchalik-parol')
"
```

> Parolni keyin admin paneldan albatta o'zgartiring.

---

## 8. Muhim: Free plan haqida

Free web service **15 daqiqa harakatsizlikdan keyin uxlaydi**. Keyingi so'rov
50+ soniya kutadi (cold start). Mobil ilova uchun bu jiddiy muammo.

Yechimlar:
- **Starter plan** ($7/oy) — uxlamaydi, Shell bor. Prod uchun tavsiya.
- Vaqtincha: tashqi ping servisi (UptimeRobot) har 10 daqiqada
  `/api/health` ga so'rov yuboradi.

Free Postgres esa **30 kundan keyin o'chadi** — ma'lumot yo'qoladi.

---

## Nima o'zgardi

| Fayl | O'zgarish |
|---|---|
| `requirements.txt` | gunicorn, whitenoise, psycopg, dj-database-url, django-storages, boto3 |
| `uyimiz/settings.py` | `DATABASE_URL` → Postgres; S3 media; WhiteNoise; `RENDER_EXTERNAL_HOSTNAME` avtomatik ALLOWED_HOSTS'ga; HSTS/secure cookies; health endpoint SSL-redirect'dan ozod; env'dan CORS; console logging |
| `uyimiz/urls.py` | media serve `DEBUG` emas, `USE_S3` ga bog'liq |
| `Dockerfile` | build: pip + collectstatic; CMD → `entrypoint.sh` |
| `entrypoint.sh` | konteyner startida: migrate → gunicorn (`$PORT`) |
| `build.sh` | faqat Python runtime uchun (hozir ishlatilmayapti) |
| `render.yaml` | Blueprint: web service + Postgres + env |
| `.env.example` | barcha env namunasi |

Lokalda hech narsa buzilmadi — `DATABASE_URL` va `AWS_STORAGE_BUCKET_NAME`
bo'lmasa sqlite + lokal media bilan eski holicha ishlaydi.

---

## Deploy'dan keyingi ishlar

Muhimlik tartibida:

**1. DRF ruxsatlarini qattiqlashtirish** — hozir
`DEFAULT_PERMISSION_CLASSES = ['AllowAny']`. Ya'ni view'da alohida
`permission_classes` yozilmagan har bir endpoint ochiq. CRM va admin
endpoint'larini tekshiring; default'ni `IsAuthenticated` qilib, ochiq
endpoint'larga (e'lonlar ro'yxati, health, OTP) view darajasida
`AllowAny` qo'yish xavfsizroq.

**2. OTP va login'ga rate limiting** — throttling yo'q. Hozircha
istalgan kishi cheksiz SMS yuborishi mumkin. DRF `DEFAULT_THROTTLE_RATES`
bilan `anon: 20/hour` darajasida cheklang.

**3. SMS provayder** — OTP konsolgami yoki real yuborilyaptimi tekshiring.
Eskiz.uz yoki Play Mobile. Ularning panelida Render IP'larini
(`74.220.50.0/24`, `74.220.58.0/24`) whitelist qiling.

**4. Token o'rniga JWT** — hozirgi DRF token muddatsiz, o'g'irlansa
abadiy amal qiladi. `djangorestframework-simplejwt` refresh/expiry beradi.

**5. Ma'lumot ko'chirish** (agar sqlite'da kerakli data bo'lsa):
```bash
python manage.py dumpdata --natural-foreign --natural-primary \
  -e contenttypes -e auth.Permission -e sessions > data.json
# Render Shell'da: python manage.py loaddata data.json
```

**6. Sentry** — `sentry-sdk[django]`, bepul tier yetarli. Render loglari
faqat oxirgi bir necha kunni saqlaydi.

**7. Backup** — Render Postgres kunlik backup oladi (Basic+ planlarda).
Haftalik `pg_dump` ni tashqariga saqlab turing.

**8. `db.sqlite3` ni git tarixidan tozalash** — `.gitignore` da bor,
lekin avval commit qilingan bo'lsa tarixda qoladi:
`git rm --cached db.sqlite3`

**9. Background job'lar** — PDF generatsiya (reportlab) hozir request
ichida ishlaydi. Sekinlashsa `django-q2` yoki Celery + Render Redis.

**10. Custom domen** — Settings → Custom Domains → `api.uyimiz.uz`.
Keyin `DJANGO_ALLOWED_HOSTS` va `DJANGO_CSRF_TRUSTED_ORIGINS` ga qo'shing.
