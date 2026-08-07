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
    return JsonResponse({'status': 'ok', 'service': 'uyimiz-backend'})


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
