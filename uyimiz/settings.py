"""
Uyimiz.uz — yagona Django backend sozlamalari.
Uch alohida backend (node-backend, django-backend/CRM, admin-backend)
shu bitta loyihaga birlashtirilgan: bitta baza, bitta auth, bitta API.
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default='0'):
    return os.environ.get(name, default).lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [x.strip() for x in os.environ.get(name, default).split(',') if x.strip()]


DEBUG = env_bool('DJANGO_DEBUG', '1')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or (
    'dev-secret-key-CHANGE-IN-PRODUCTION-uyimiz-uz' if DEBUG else ''
)
if not SECRET_KEY:
    raise RuntimeError('DJANGO_SECRET_KEY majburiy (DEBUG=0 rejimida).')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', '*' if DEBUG else '')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS') + [
    'https://*.vercel.app',
    'https://*.uyimiz.uz',
]

# Render har bir servisga <name>.onrender.com domenini beradi va uni
# RENDER_EXTERNAL_HOSTNAME env'iga avtomatik yozadi.
RENDER_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_HOSTNAME:
    ALLOWED_HOSTS += [RENDER_HOSTNAME, '.onrender.com']
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_HOSTNAME}')
    # Render'ning ichki health-check'i lokal manzilga so'rov yuboradi.
    ALLOWED_HOSTS += ['localhost', '127.0.0.1', '[::1]']

# Render proxy HTTPS'ni tugatadi va X-Forwarded-Proto yuboradi.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',

    # Uyimiz.uz — yagona backend ilovalari
    'accounts',
    'core',
    'listings',
    'crm',
    'platform_admin',
    'ratings',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'uyimiz.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'uyimiz.wsgi.application'
ASGI_APPLICATION = 'uyimiz.asgi.application'

# ───────────────────────── Baza ─────────────────────────
# DATABASE_URL bo'lsa — Postgres (Fly.io / Supabase / Neon).
# Bo'lmasa — lokal ishlab chiqish uchun sqlite.
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=env_bool('DJANGO_DB_SSL', '0'),
    )
}

# ⚠️ PROD'DA SQLITE = MA'LUMOT YO'QOLISHI.
#
# Render/Fly konteynerining diski vaqtinchalik: servis qayta ishga
# tushganda (deploy, bepul tarifdagi "uyqu", yoki oddiy restart) sqlite
# fayli yangisiga almashadi. Natijada BARCHA foydalanuvchi, token va
# e'lon o'chadi — ilova esa buni "token eskirdi" deb tushunib, odamdan
# qaytadan ro'yxatdan o'tishni so'raydi.
#
# Shu sababli DEBUG=0 rejimida sqlite aniqlansa, ishga tushish paytida
# baland ovozda ogohlantiramiz va /api/health ni "error" holatiga
# o'tkazamiz (health tekshiruvi settings.DATABASES ni o'qiydi).
DB_IS_EPHEMERAL_SQLITE = (
    not DEBUG and DATABASES['default']['ENGINE'].endswith('sqlite3')
)
if DB_IS_EPHEMERAL_SQLITE:
    import sys

    print(
        '\n'
        '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        '!!!  DATABASE_URL berilmagan — vaqtinchalik SQLITE ishlatilmoqda.\n'
        '!!!  Servis qayta ishga tushganda BARCHA MA\'LUMOT O\'CHADI:\n'
        '!!!  foydalanuvchilar, tokenlar, e\'lonlar, shartnomalar.\n'
        '!!!  Foydalanuvchilar "qaytadan ro\'yxatdan o\'ting" xabarini oladi.\n'
        '!!!\n'
        '!!!  Yechim: Render → Environment → DATABASE_URL ga Postgres\n'
        '!!!  ulanish satrini qo\'ying (RENDER-POSTGRES.md ga qarang).\n'
        '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n',
        file=sys.stderr,
        flush=True,
    )

AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = [
    'accounts.backends.PhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# ──────────────────── Static va Media ────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# AWS_STORAGE_BUCKET_NAME berilgan bo'lsa — media fayllar
# Tigris/S3'ga yoziladi (deploy'da yo'qolmaydi). Aks holda lokal disk.
USE_S3 = bool(os.environ.get('AWS_STORAGE_BUCKET_NAME'))

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

if USE_S3:
    AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL_S3', 'https://t3.storage.dev')
    AWS_S3_REGION_NAME = os.environ.get('AWS_REGION', 'auto')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False  # rasm URL'lari ochiq (imzosiz) bo'lsin
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

    STORAGES['default'] = {'BACKEND': 'storages.backends.s3.S3Storage'}

    _custom_domain = os.environ.get('AWS_S3_CUSTOM_DOMAIN')
    if _custom_domain:
        AWS_S3_CUSTOM_DOMAIN = _custom_domain
        MEDIA_URL = f'https://{_custom_domain}/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ───────────────────────── DRF ─────────────────────────

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    # OTP, login va imzo endpointlariga cheklov — SMS spami va parol
    # brute-force'ining oldini oladi. Klasslar: uyimiz/throttling.py,
    # view'larda @throttle_classes([...]) orqali qo'llanadi.
    'DEFAULT_THROTTLE_RATES': {
        'otp': os.environ.get('THROTTLE_OTP', '10/hour'),
        'login': os.environ.get('THROTTLE_LOGIN', '20/hour'),
        'sign': os.environ.get('THROTTLE_SIGN', '15/hour'),
    },
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_RENDERER_CLASSES': (
        ['rest_framework.renderers.JSONRenderer', 'rest_framework.renderers.BrowsableAPIRenderer']
        if DEBUG else
        ['rest_framework.renderers.JSONRenderer']
    ),
}

# ───────────────────────── CORS ─────────────────────────
# Mobil ilova, agent CRM va admin panel — barchasi shu bitta backendga murojaat qiladi.
CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL', '1' if DEBUG else '0')
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True

# Vercel har bir deploy uchun alohida preview domen beradi
# (masalan uyimiz-admin-git-main-abduhafiz.vercel.app) — barchasini qamrash
# uchun regex ishlatiladi. Lokal dev portlari ham shu yerda.
CORS_ALLOWED_ORIGIN_REGEXES = env_list('CORS_ALLOWED_ORIGIN_REGEXES') + [
    r'^https://.*\.vercel\.app$',
    r'^https://.*\.netlify\.app$',
    r'^https://.*\.uyimiz\.uz$',
    r'^http://localhost:\d+$',
    r'^http://127\.0\.0\.1:\d+$',
]

# Rasm/PDF'ni <canvas> yoki fetch orqali o'qish uchun media javoblariga ham
# CORS sarlavhasi kerak bo'ladi.
CORS_URLS_REGEX = r'^/(api|media)/.*$'

FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# ─────────────────────── SMS / OTP rejimi ───────────────────────
# SMS provayder (Eskiz.uz va h.k.) hali ulanmagan. Shu sababli tizimni
# sinab ko'rish uchun "test rejimi" bor: OTP kodi SMS o'rniga API
# javobining o'zida qaytariladi va ilova uni ekranda ko'rsatadi.
#
#   OTP_TEST_MODE=1  → kod javobda keladi (SMS kerak emas)
#   OTP_TEST_MODE=0  → kod faqat server logida (real SMS kutiladi)
#
# Sukut bo'yicha: DEBUG=1 da yoqilgan, prod'da o'chirilgan.
#
# ⚠️ OMMAGA OCHISHDAN OLDIN buni albatta 0 ga o'tkazing — aks holda
# istalgan kishi istalgan raqam bilan kira oladi.
OTP_TEST_MODE = env_bool('OTP_TEST_MODE', '1' if DEBUG else '0')

# SMS provayder ulangach 1 qilinadi. Hozircha kod faqat logga yoziladi.
SMS_ENABLED = env_bool('SMS_ENABLED', '0')

# ─────────────────── Xavfsizlik (faqat prod) ───────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', '1')
    # Render'ning health-check'i ichki HTTP orqali keladi — redirect qilinmasin,
    # aks holda 301 qaytadi va deploy "unhealthy" deb hisoblanadi.
    SECURE_REDIRECT_EXEMPT = [r'^api/health/?$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

# ───────────────────────── Logging ─────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{levelname}] {asctime} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
    },
}
