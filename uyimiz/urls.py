"""Uyimiz.uz — yagona API xaritasi.

Barcha uch tomon (mobil ilova foydalanuvchisi, Uyimiz Agent, admin panel)
shu bitta manzillar jadvaliga, bitta bazaga murojaat qiladi:

  /api/auth/...      — umumiy autentifikatsiya (OTP: user, parol: agent/admin)
  /api/...           — asosiy ilova: e'lonlar, sevimlilar, chat, shartnoma
  /api/crm/...       — Uyimiz Agent CRM (faqat role=agent)
  /api/admin/...     — Admin panel (faqat role=admin/superadmin)
  /api/ratings/...   — reyting tizimi
  /admin/            — Django ichki admin (superuser uchun qulay panel)
"""
from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve


def health(request):
    """Servis holati va diagnostika.

    Nimadir ishlamasa birinchi shu manzilni oching — u aynan nima
    sozlanmaganini aytadi (baza ulanmagan, migratsiya bajarilmagan,
    media storage yo'q va h.k.).
    """
    from django.conf import settings as st
    from django.db import connection

    info = {
        'status': 'ok',
        'service': 'uyimiz-backend',
        'debug': st.DEBUG,
        'otpTestMode': st.OTP_TEST_MODE,
        'smsEnabled': st.SMS_ENABLED,
        'mediaStorage': 's3' if st.USE_S3 else 'local (deploy\'da o\'chadi)',
    }
    problems = []

    # 1) Baza ulanadimi
    engine = st.DATABASES['default']['ENGINE'].rsplit('.', 1)[-1]
    info['database'] = engine
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
        info['databaseConnected'] = True
    except Exception as exc:  # noqa: BLE001 — sabab foydalanuvchiga kerak
        info['databaseConnected'] = False
        problems.append(f'Bazaga ulanib bo\'lmadi: {exc}')

    if engine == 'sqlite3':
        problems.append(
            'DATABASE_URL berilmagan — vaqtinchalik sqlite ishlatilmoqda, '
            'server qayta ishga tushganda hamma ma\'lumot o\'chadi.'
        )

    # 2) Migratsiyalar bajarilganmi
    if info.get('databaseConnected'):
        try:
            from django.db.migrations.executor import MigrationExecutor

            executor = MigrationExecutor(connection)
            pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
            info['pendingMigrations'] = len(pending)
            if pending:
                problems.append(
                    f'{len(pending)} ta migratsiya bajarilmagan — '
                    'jadvallar yo\'q, API 500 qaytaradi.'
                )
        except Exception as exc:  # noqa: BLE001
            problems.append(f'Migratsiya holatini o\'qib bo\'lmadi: {exc}')

    # 3) Prod'dagi xavfli sozlamalar
    if not st.DEBUG:
        if st.OTP_TEST_MODE:
            problems.append(
                'OTP_TEST_MODE=1 — kod javobda ochiq qaytmoqda. '
                'Sinov uchun to\'g\'ri, ommaga ochishdan oldin 0 qiling.'
            )
        if st.CORS_ALLOW_ALL_ORIGINS:
            problems.append('CORS_ALLOW_ALL=1 — barcha saytlarga ochiq.')

    info['problems'] = problems
    if any('ulanib bo\'lmadi' in p or 'migratsiya bajarilmagan' in p for p in problems):
        info['status'] = 'error'
    elif problems:
        info['status'] = 'warning'

    return JsonResponse(info, json_dumps_params={'ensure_ascii': False})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health', health),

    path('api/auth/', include('accounts.urls')),
    path('api/', include('core.urls')),
    path('api/', include('listings.urls')),
    path('api/crm/', include('crm.urls')),
    path('api/admin/', include('platform_admin.urls')),
    path('api/ratings/', include('ratings.urls')),
]

# Media: S3/Tigris ishlatilmasa, fayllarni Django o'zi tarqatadi
# (lokal ishlab chiqish yoki Fly Volume rejimi uchun).
if not settings.USE_S3:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
