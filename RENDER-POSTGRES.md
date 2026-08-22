# Ro'yxatdan chiqarib yuborish muammosini bartaraf qilish

## Muammo nima edi

Foydalanuvchi ro'yxatdan o'tadi, bir necha daqiqadan keyin ilova uni
chiqarib yuboradi va qaytadan ro'yxatdan o'tishni so'raydi.

**Bu kod xatosi emas.** Sabab — backend hozir vaqtinchalik `sqlite`
faylida ishlayapti. O'zingiz tekshirib ko'ring:

```
https://uyimiz-backend.onrender.com/api/health
```

Javob:

```json
{
  "database": "sqlite3",
  "problems": [
    "DATABASE_URL berilmagan — vaqtinchalik sqlite ishlatilmoqda,
     server qayta ishga tushganda hamma ma'lumot o'chadi."
  ]
}
```

Render konteynerining diski **vaqtinchalik**. Servis qayta ishga tushganda
(deploy, bepul tarifdagi "uyqu"dan uyg'onish, oddiy restart) `db.sqlite3`
fayli yangisiga almashadi. Ya'ni:

| Nima o'chadi | Foydalanuvchi nimani ko'radi |
|---|---|
| `accounts_user` jadvali | Hisob yo'qoladi |
| `authtoken_token` jadvali | Ilovadagi token yaroqsiz → 401 |
| `listings_listing` | E'lonlar g'oyib bo'ladi |
| `listings_contract` | Shartnomalar g'oyib bo'ladi |

Ilova 401 ni ko'rib "token eskirgan" deb hisoblaydi va kirish oynasini
ochadi. Tashqaridan bu "ro'yxatdan o'tish ishlamayapti"ga o'xshaydi.

**Yechim: doimiy Postgres ulash.** Bu bitta env o'zgaruvchisi.

---

## Qadamlar (taxminan 10 daqiqa)

### 1. Postgres yaratish

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **Postgres**
2. Sozlamalar:
   - **Name**: `uyimiz-db`
   - **Database**: `uyimiz`
   - **User**: `uyimiz`
   - **Region**: `Frankfurt (EU Central)` — backend bilan **bir xil region**
     bo'lishi shart, aks holda ichki ulanish ishlamaydi
   - **Plan**: `Free` (sinov uchun) yoki `Basic-256MB` (doimiy uchun)
3. **Create Database** → holati `Available` bo'lguncha kuting (~2 daqiqa)

> ⚠️ **Free Postgres 30 kundan keyin o'chadi** va Render buni oldindan
> pochtaga yozadi. Ommaga ochishdan oldin `Basic-256MB` ga o'ting
> (oyiga ~$6). Ma'lumot saqlanadi, faqat plan almashadi.

### 2. Ulanish satrini nusxalash

Yaratilgan bazaning sahifasida **Connections** bo'limi bor. U yerdan
**Internal Database URL** ni nusxalang (External emas — ichkisi tezroq va
bepul):

```
postgresql://uyimiz:xxxxxxxx@dpg-xxxxx-a/uyimiz
```

### 3. Backendga ulash

1. `uyimiz-backend` servisi → **Environment**
2. **Add Environment Variable**:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | 2-qadamdagi Internal Database URL |

3. Shu yerda quyidagilarni ham to'g'rilang (hozir noto'g'ri turibdi):

   | Key | Value | Nega |
   |---|---|---|
   | `DJANGO_DEBUG` | `0` | Hozir `1` — xato izlari va SQL so'rovlari ommaga ochiq ko'rinmoqda |
   | `DJANGO_SECRET_KEY` | uzun tasodifiy satr | `DEBUG=0` da majburiy |
   | `DJANGO_ALLOWED_HOSTS` | `uyimiz-backend.onrender.com` | |
   | `ADMIN_PHONE` | `+998XXXXXXXXX` | Admin panelga kirish uchun |
   | `ADMIN_PASSWORD` | kamida 8 belgi | Konteyner ishga tushganda hisob avtomatik yaratiladi |
   | `OTP_TEST_MODE` | sinovda `1`, ommaga ochishda `0` | `1` da SMS kod javobda ochiq keladi |

   `DJANGO_SECRET_KEY` uchun kalit generatsiya qilish:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

4. **Save Changes** → servis avtomatik qayta deploy bo'ladi

### 4. Tekshirish

Deploy tugagach:

```
https://uyimiz-backend.onrender.com/api/health
```

Kutilgan javob:

```json
{
  "status": "ok",
  "debug": false,
  "database": "postgresql",
  "databaseConnected": true,
  "pendingMigrations": 0,
  "problems": []
}
```

`"database": "postgresql"` va `"problems": []` ko'rinsa — tayyor.
Endi ro'yxatdan o'tgan foydalanuvchi hisobi joyida qoladi.

---

## Qolgan ikkita ogohlantirish

### Rasm fayllari ham yo'qoladi

`"mediaStorage": "local (deploy'da o'chadi)"` — yuklangan uy rasmlari va
avatarlar ham konteyner bilan birga o'chadi. Baza tuzatilgach shu ham
kerak bo'ladi.

Yechim — S3-mos object storage (Cloudflare R2 bepul 10 GB beradi):

| Key | Value |
|---|---|
| `AWS_STORAGE_BUCKET_NAME` | bucket nomi |
| `AWS_ACCESS_KEY_ID` | kalit |
| `AWS_SECRET_ACCESS_KEY` | maxfiy kalit |
| `AWS_ENDPOINT_URL_S3` | `https://<account>.r2.cloudflarestorage.com` |
| `AWS_REGION` | `auto` |

Kod tomonida hech narsa o'zgartirish shart emas — `settings.py` bu
o'zgaruvchilar borligini o'zi sezadi va S3 ga o'tadi.

### Bepul tarifdagi "uyqu"

Render Free tarifidagi web servis 15 daqiqa harakatsizlikdan keyin
uxlaydi. Keyingi so'rov 30–60 soniya kutadi. Postgres ulangach ma'lumot
yo'qolmaydi, lekin birinchi ochilish sekin bo'ladi.

Buning ikki yechimi bor:

1. `Starter` tarifga o'tish (~$7/oy) — uxlamaydi
2. Har 10 daqiqada `/api/health` ga so'rov yuborib turish
   (masalan [cron-job.org](https://cron-job.org) bepul)

---

## Nega Supabase emas

Siz Supabase'ni taklif qilgandingiz — bu ham ishlaydi, lekin bu holatda
kerak emas edi:

- Muammo Django backendda emas, **DATABASE_URL berilmaganida** edi
- Supabase'ga to'liq o'tish uchun auth, chat, storage va uch frontend
  qaytadan yozilishi kerak bo'lardi
- Agar keyinchalik xohlasangiz, Supabase'ning Postgres'idan **shu backend
  uchun baza sifatida** foydalansangiz ham bo'ladi: `DATABASE_URL` ga
  Supabase'ning `Connection string → URI` qiymatini qo'yasiz, xolos
  (bu holda `DJANGO_DB_SSL=1` qiling)
