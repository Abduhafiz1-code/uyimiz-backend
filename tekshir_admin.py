"""Admin panel API'sini tekshiruvchi skript.

Admin panel (Uyimiz.uz_Admin) yuboradigan so'rovlarni aynan o'shanday
takrorlaydi — shu tufayli "brauzerda bosganda ishlamadi" turidagi xatolar
shu yerda ushlanadi.

Ishlatish:  python tekshir_admin.py
Bazaga tegmaydi — Django'ning test bazasida ishlaydi va tugagach o'chiradi.
"""
import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uyimiz.settings')
os.environ.setdefault('DJANGO_DEBUG', '1')
django.setup()

from django.test.runner import DiscoverRunner  # noqa: E402
from django.test.utils import setup_test_environment, teardown_test_environment  # noqa: E402


def main():
    setup_test_environment()
    runner = DiscoverRunner(verbosity=0, interactive=False)
    old_config = runner.setup_databases()

    from django.test import Client  # noqa: E402

    from accounts.models import AdminTitle, CertificationStatus, Role, User  # noqa: E402
    from listings.models import Listing, ListingStatus  # noqa: E402
    from platform_admin.models import ModerationItem, Tariff  # noqa: E402

    ok, fail = [], []

    def check(label, condition, extra=''):
        (ok if condition else fail).append(label)
        mark = 'OK  ' if condition else 'XATO'
        print(f'  [{mark}] {label}' + (f'  → {extra}' if extra and not condition else ''))

    # ── ma'lumot tayyorlash ────────────────────────────────────────────
    superadmin = User.objects.create_superuser(
        phone='+998901230001', password='SuperParol123', name='Bosh Admin',
    )
    agent = User.objects.create_user(
        phone='+998901230002', name='Agent Aliyev', role=Role.AGENT,
        certification=CertificationStatus.KUTILMOQDA, district='chilonzor',
        commission_rate=2, rating=4.5,
    )
    user = User.objects.create_user(phone='+998901230003', name='Oddiy Foydalanuvchi')
    listing = Listing.objects.create(
        owner=user, district='chilonzor', address='Test 1', price=1000,
        status=ListingStatus.PENDING,
    )
    ModerationItem.objects.create(listing=listing, reason='AI shubha', score=85)
    Tariff.objects.create(name='VIP', price_label='50 000', period='hafta', description='Tepada')

    c = Client()

    # ── 1. Login ───────────────────────────────────────────────────────
    print('\n1) Admin panelga kirish')
    r = c.post(
        '/api/auth/login/',
        {'phone': '+998901230001', 'password': 'SuperParol123'},
        content_type='application/json',
    )
    check('to\'g\'ri parol bilan kiriladi', r.status_code == 200, r.content[:200])
    body = r.json()
    check('rol superadmin qaytadi', body.get('role') == 'superadmin', body.get('role'))
    token = body['token']

    r = c.post(
        '/api/auth/login/',
        {'phone': '+998901230001', 'password': 'notogri'},
        content_type='application/json',
    )
    check('noto\'g\'ri parol rad etiladi (400)', r.status_code == 400, r.status_code)

    H = {'HTTP_AUTHORIZATION': f'Token {token}'}

    def get(path):
        return c.get(path, **H)

    def send(method, path, data=None):
        fn = getattr(c, method)
        return fn(path, data if data is not None else {}, content_type='application/json', **H)

    # ── 2. Ma'lumot yuklash (panel ochilganda) ─────────────────────────
    print('\n2) Panel ochilganda yuklanadigan barcha endpointlar')
    for path in [
        '/api/admin/users/', '/api/admin/admins/', '/api/admin/agents/',
        '/api/admin/posts/', '/api/admin/moderation/', '/api/admin/tariffs/',
        '/api/admin/settings', '/api/admin/audit', '/api/admin/dashboard',
    ]:
        r = get(path)
        check(f'{path} ochiladi', r.status_code == 200, f'{r.status_code} {r.content[:120]}')

    r = get('/api/admin/dashboard')
    d = r.json()
    check('dashboard barcha maydonlarni qaytaradi',
          all(k in d for k in ('usersTotal', 'activeAgents', 'postsToday', 'moderationCount',
                               'postsTotal', 'dealsTotal', 'stage')), list(d))

    # ── 3. Ruxsatlar ───────────────────────────────────────────────────
    print('\n3) Ruxsat nazorati')
    r = c.get('/api/admin/users/')
    check('tokensiz admin API yopiq', r.status_code in (401, 403), r.status_code)

    from rest_framework.authtoken.models import Token

    user_token = Token.objects.create(user=user).key
    r = c.get('/api/admin/users/', HTTP_AUTHORIZATION=f'Token {user_token}')
    check('oddiy foydalanuvchi admin APIga kira olmaydi', r.status_code == 403, r.status_code)

    # ── 4. Foydalanuvchi amallari ──────────────────────────────────────
    print('\n4) Foydalanuvchini boshqarish')
    r = send('patch', f'/api/admin/users/{user.id}/', {'name': 'Yangi Ism', 'phone': user.phone})
    check('foydalanuvchi tahrirlanadi (PATCH)', r.status_code == 200, r.content[:200])
    check('ism o\'zgardi', r.json().get('name') == 'Yangi Ism', r.json().get('name'))

    r = send('patch', f'/api/admin/users/{user.id}/toggle-block/')
    check('bloklash ishlaydi', r.status_code == 200, r.content[:200])
    check('holat "Bloklangan" ga o\'zgardi', r.json().get('status') == 'Bloklangan', r.json().get('status'))
    send('patch', f'/api/admin/users/{user.id}/toggle-block/')

    # ── 5. Agent amallari ──────────────────────────────────────────────
    print('\n5) Agentni boshqarish')
    r = send('patch', f'/api/admin/agents/{agent.id}/', {'name': 'Agent A.', 'commission_rate': 1.5})
    check('agent tahrirlanadi (PATCH — panel aynan shuni yuboradi)',
          r.status_code == 200, r.content[:200])
    check('komissiya saqlandi', str(r.json().get('commission_rate')) == '1.50',
          r.json().get('commission_rate'))

    r = send('patch', f'/api/admin/agents/{agent.id}/approve/')
    check('agent sertifikatlanadi', r.status_code == 200, r.content[:200])
    check('sertifikat "Tasdiqlangan"', r.json().get('certification') == 'Tasdiqlangan',
          r.json().get('certification'))

    # Sertifikatlangach saytdagi ochiq katalogda ko'rinishi kerak.
    r = c.get('/api/agents')
    names = [a['name'] for a in r.json()['items']]
    check('tasdiqlangan agent ommaviy katalogga tushdi', 'Agent A.' in names, names)

    r = send('patch', f'/api/admin/agents/{agent.id}/revoke/')
    check('sertifikat bekor qilinadi', r.status_code == 200, r.content[:200])
    r = c.get('/api/agents')
    check('bekor qilingach katalogdan chiqib ketdi', r.json()['total'] == 0, r.json()['total'])

    # ── 6. E'lon va moderatsiya ────────────────────────────────────────
    print('\n6) E\'lon va moderatsiya')
    item = ModerationItem.objects.first()
    r = send('patch', f'/api/admin/moderation/{item.id}/approve/')
    check('moderatsiyada tasdiqlanadi', r.status_code == 200, r.content[:200])
    listing.refresh_from_db()
    check('e\'lon "active" holatiga o\'tdi', listing.status == 'active', listing.status)

    r = send('patch', f'/api/admin/posts/{listing.id}/approve/')
    check('e\'lon tasdiqlanadi', r.status_code == 200, r.content[:200])
    r = c.delete(f'/api/admin/posts/{listing.id}/', **H)
    check('e\'lon o\'chiriladi', r.status_code in (200, 204), r.status_code)

    # ── 7. Admin hisoblari ─────────────────────────────────────────────
    print('\n7) Admin hisoblari')
    r = send('post', '/api/admin/admins/', {
        'name': 'Yangi Moderator', 'phone': '+998901230009',
        'admin_title': 'Moderator', 'is_active': True, 'password': 'ParolBu123',
    })
    check('parol bilan admin qo\'shiladi', r.status_code in (200, 201), r.content[:200])
    new_id = r.json().get('id')

    # PAROLSIZ yaratish — bu yerda Django 5.1 da olib tashlangan
    # make_random_password() chaqirilardi va 500 qaytardi.
    r = send('post', '/api/admin/admins/', {
        'name': 'Parolsiz Admin', 'phone': '+998901230010',
        'admin_title': 'Admin', 'is_active': True, 'password': '',
    })
    check('PAROLSIZ admin qo\'shish 500 bermaydi', r.status_code in (200, 201),
          f'{r.status_code} {r.content[:160]}')

    r = send('patch', f'/api/admin/admins/{new_id}/', {
        'name': 'Moderator O.', 'phone': '+998901230009',
        'admin_title': 'Moderator', 'is_active': True,
    })
    check('parolsiz tahrirlash ishlaydi (PATCH)', r.status_code == 200, r.content[:200])

    r = c.delete(f'/api/admin/admins/{new_id}/', **H)
    check('admin o\'chiriladi', r.status_code in (200, 204), r.status_code)

    # ── 8. Sozlamalar va tariflar ──────────────────────────────────────
    print('\n8) Sozlamalar va tariflar')
    r = send('put', '/api/admin/settings', {'ai_threshold': 77})
    check('bitta sozlama saqlanadi', r.status_code == 200, r.content[:200])
    check('qiymat o\'zgardi', r.json().get('ai_threshold') == 77, r.json().get('ai_threshold'))

    tariff = Tariff.objects.first()
    r = send('put', f'/api/admin/tariffs/{tariff.id}/', {
        'name': 'VIP', 'price_label': '60 000', 'period': 'hafta', 'description': 'Tepada',
    })
    check('tarif saqlanadi', r.status_code == 200, r.content[:200])

    # ── 9. Audit jurnali ───────────────────────────────────────────────
    print('\n9) Audit jurnali')
    r = get('/api/admin/audit')
    items = r.json() if isinstance(r.json(), list) else r.json().get('results', [])
    check('bajarilgan amallar qayd etildi', len(items) > 0, len(items))
    if items:
        check('yozuvda admin ismi bor', bool(items[0].get('admin_name')), items[0])

    # ── xulosa ─────────────────────────────────────────────────────────
    print(f'\n{"=" * 52}\nJami: {len(ok)} ta o\'tdi, {len(fail)} ta yiqildi')
    if fail:
        print('Yiqilganlari:')
        for f in fail:
            print('  •', f)

    runner.teardown_databases(old_config)
    teardown_test_environment()
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
