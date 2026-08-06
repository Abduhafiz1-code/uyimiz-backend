# Uyimiz.uz — Yagona Django Backend

Bu loyiha ilgari **uchta alohida backend** (`node-backend` — asosiy ilova,
`django-backend` — agent CRM, `admin-backend` — admin panel) o'rniga yaratilgan
**bitta butun Django backend**. Bitta baza, bitta autentifikatsiya tizimi,
bitta API — oddiy foydalanuvchi ham, Uyimiz Agent ham, admin/superadmin ham
shu bitta backendga, bitta `User` jadvaliga murojaat qiladi.

## Nega "bitta butun" backend?

- **Bitta `User` modeli** (`accounts/models.py`) — user, agent, admin, superadmin
  bitta jadvalda, faqat `role` maydoni bilan ajraladi. Token ham bitta xil
  (`Authorization: Token <key>`), shuning uchun uchala tomon ham bir xil
  auth orqali kiradi.
- **Bitta baza** — CRM'dagi bitim yopilishi bilan asosiy ilovadagi shartnoma,
  reyting va admin paneldagi statistika avtomatik yangilanadi (hammasi bir-biriga
  FK orqali bog'langan, alohida servislar orasida HTTP sinxronizatsiya yo'q).
- **Bitta Django loyiha, oltita ilova** — hech biri mustaqil server emas,
  hammasi bitta `manage.py runserver` bilan ishga tushadi.

## Ilovalar tuzilishi

| Ilova | Vazifasi | Eski backend o'rnini bosadi |
|---|---|---|
| `accounts` | Yagona foydalanuvchi, OTP, login, token | — (yangi, uchalasini birlashtiradi) |
| `core` | Tumanlar, umumiy sozlamalar, demo seed | — |
| `listings` | E'lonlar, sevimlilar, chat, onlayn shartnoma (PDF) | `node-backend` |
| `crm` | Agent CRM: mijozlar, obyektlar, bitimlar, ko'rsatuvlar | `django-backend` |
| `platform_admin` | Admin panel: moderatsiya, tariflar, sozlamalar, audit | `admin-backend` |
| `ratings` | Bitimdan keyingi o'zaro baholash tizimi | — (docx'dagi yetishmagan funksiya) |

## `Uyimiz_uz.docx` asosida qo'shilgan yangi funksiyalar

Hujjatdagi biznes-rejaga ko'ra, eski backendlarda yo'q bo'lgan quyidagilar qo'shildi:

1. **Onlayn shartnoma + real PDF generatsiyasi** (`listings/pdf.py`, reportlab) —
   xaridor shartnomani imzolagach, haqiqiy PDF fayl yaratiladi.
2. **Reyting tizimi** (`ratings` ilovasi) — bitim yopilgach tomonlar bir-birini
   baholaydi, agent/e'lon reytingi avtomatik yangilanadi.
3. **Avtomatik lead taqsimoti** (`crm/services.py`) — yangi mijoz hudud va
   reyting bo'yicha eng mos agentga avtomatik biriktiriladi
   (`POST /api/crm/leads/` — mobil ilova/Telegram bot uchun ochiq endpoint).
4. **Platforma sozlamalari singleton** (`platform_admin/models.py`) — komissiya
   foizi, VIP/Premium narxlari, shartnoma xizmat haqi, biznes bosqichi (1/2/3) —
   docx 3- va 4-bandlaridagi moliyaviy modelga mos.
5. **Audit jurnali** — har bir admin harakati avtomatik yoziladi (shaffoflik).
6. **Agent darajalari (tier)** — Yangi → Faol → Tajribali → Top, yopilgan
   bitimlar soniga qarab avtomatik hisoblanadi.

## O'rnatish

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo        # demo ma'lumotlar bilan to'ldiradi
python manage.py createsuperuser  # xohlasangiz, qo'shimcha Django /admin/ uchun
python manage.py runserver
```

Server: `http://localhost:8000/`
Django ichki admin (fayllarni tez ko'rish uchun qulay): `http://localhost:8000/admin/`

### Demo login (`seed_demo` yaratadi)

| Rol | Telefon | Parol |
|---|---|---|
| Superadmin | +998900000001 | admin12345 |
| Admin | +998900000002 | admin12345 |
| Moderator | +998900000003 | admin12345 |
| Uyimiz Agent | +998901111000 | agent12345 |
| Oddiy foydalanuvchi | ixtiyoriy raqam | SMS-kod orqali (`/api/auth/send-code`) |

## API xaritasi (qisqacha)

```
POST /api/auth/send-code          — oddiy foydalanuvchi: SMS-kod yuborish
POST /api/auth/verify             — kodni tasdiqlash, token olish
POST /api/auth/login/             — agent/admin: telefon+parol bilan token olish
GET/PATCH /api/auth/me            — o'z profili (har qanday rol)
POST /api/auth/logout             — tokenni bekor qilish

GET    /api/districts             — tumanlar ro'yxati
GET    /api/listings/             — e'lonlar (filtr: deal, district, rooms, priceMin/Max, q, sort)
POST   /api/listings/             — yangi e'lon (login talab qilinadi)
GET    /api/listings/{id}/        — bitta e'lon (views +1)
POST   /api/listings/{id}/photos  — rasm yuklash
GET    /api/me/listings           — mening e'lonlarim
GET/POST /api/favorites           — sevimlilar
POST   /api/favorites/{id}        — sevimliga qo'shish/olib tashlash
GET/POST /api/listings/{id}/chat  — e'lon bo'yicha suhbat
POST   /api/listings/{id}/contract — onlayn shartnoma yaratish
POST   /api/contracts/{id}/sign   — shartnomani imzolash (PDF generatsiya qilinadi)
POST   /api/ratings/contracts/{id}/rate — bitimdan keyin baholash

GET    /api/crm/dashboard/        — agent bosh sahifasi
GET    /api/crm/rating/           — agent reytingi va peshqadamlar
/api/crm/clients/, /properties/, /deals/, /showings/, /activities/ — to'liq CRUD
POST   /api/crm/leads/            — tashqi tizimdan avtomatik lead qabul qilish

GET    /api/admin/dashboard       — umumiy statistika
/api/admin/users/, /agents/, /posts/, /moderation/, /tariffs/, /admins/ — to'liq CRUD
GET/PUT /api/admin/settings       — platforma sozlamalari
GET    /api/admin/audit           — audit jurnali
```

## Eslatmalar

- Demo muhitda SMS haqiqatda yuborilmaydi — `send-code` javobida `demoCode`
  maydoni qaytadi (production'da SMS-provayder integratsiyasi qo'shiladi).
- Kelgusida (docx yo'l xaritasi, 3-bosqich): to'lov tizimi (Payme/Click),
  Telegram bot va E-IMZO integratsiyasi — hozircha shu backend ularni
  qabul qilishga tayyor struktura bilan ta'minlangan (`PlatformSettings`,
  `Contract.pdf`, `crm/services.py`).
