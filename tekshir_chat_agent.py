"""Yangi endpointlarni tekshiruvchi skript (agentlar katalogi + chat).

Ishlatish:  python tekshir_chat_agent.py

Bazaga tegmaydi — Django'ning test bazasida ishlaydi va tugagach o'chiradi.
"""
import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uyimiz.settings')
os.environ.setdefault('DJANGO_DEBUG', '1')
django.setup()

from django.test.utils import setup_test_environment, teardown_test_environment  # noqa: E402
from django.test.runner import DiscoverRunner  # noqa: E402


def main():
    setup_test_environment()
    runner = DiscoverRunner(verbosity=0, interactive=False)
    old_config = runner.setup_databases()

    from django.test import Client  # noqa: E402
    from rest_framework.authtoken.models import Token  # noqa: E402

    from accounts.models import CertificationStatus, Role, User  # noqa: E402
    from listings.models import Listing, ListingStatus  # noqa: E402

    ok, fail = [], []

    def check(label, condition, extra=''):
        (ok if condition else fail).append(label)
        mark = 'OK  ' if condition else 'XATO'
        print(f'  [{mark}] {label}' + (f'  → {extra}' if extra and not condition else ''))

    # ── ma'lumot tayyorlash ────────────────────────────────────────────
    agent = User.objects.create_user(
        phone='+998901110001', name='Test Agent', role=Role.AGENT,
        certification=CertificationStatus.TASDIQLANGAN, district='chilonzor',
        rating=4.8, rating_count=10, total_deals=25, tier='Top',
    )
    pending_agent = User.objects.create_user(
        phone='+998901110002', name='Kutayotgan Agent', role=Role.AGENT,
        certification=CertificationStatus.KUTILMOQDA, district='yunusobod',
    )
    buyer = User.objects.create_user(phone='+998901110003', name='Xaridor')
    owner = User.objects.create_user(phone='+998901110004', name='Uy egasi')

    listing = Listing.objects.create(
        owner=owner, agent=agent, district='chilonzor', address='Test ko\'chasi 1',
        price=50000, rooms=3, area=80, status=ListingStatus.ACTIVE,
    )

    buyer_token = Token.objects.create(user=buyer).key
    owner_token = Token.objects.create(user=owner).key
    agent_token = Token.objects.create(user=agent).key

    c = Client()

    def get(path, token=None, **kw):
        headers = {'HTTP_AUTHORIZATION': f'Token {token}'} if token else {}
        return c.get(path, **headers, **kw)

    def post(path, data=None, token=None):
        headers = {'HTTP_AUTHORIZATION': f'Token {token}'} if token else {}
        return c.post(path, data or {}, content_type='application/json', **headers)

    # ── 1. Ochiq agentlar katalogi ─────────────────────────────────────
    print('\n1) /api/agents — ochiq agentlar katalogi')
    r = get('/api/agents')
    check('autentifikatsiyasiz ochiladi (200)', r.status_code == 200, r.status_code)
    data = r.json()
    names = [a['name'] for a in data.get('items', [])]
    check('tasdiqlangan agent ro\'yxatda', 'Test Agent' in names, names)
    check('tasdiqlanmagan agent ro\'yxatda YO\'Q', 'Kutayotgan Agent' not in names, names)
    check('oddiy foydalanuvchi ro\'yxatda YO\'Q', 'Xaridor' not in names, names)

    first = data['items'][0]
    check('reyting qaytadi', str(first.get('rating')) == '4.8', first.get('rating'))
    check('bitimlar soni qaytadi', first.get('deals') == 25, first.get('deals'))
    check('"top" bayrog\'i hisoblanadi', first.get('top') is True, first.get('top'))
    check('faol e\'lonlar soni qaytadi', first.get('listings_count') == 1, first.get('listings_count'))

    r = get('/api/agents?district=yunusobod')
    check('tuman filtri ishlaydi', r.json()['total'] == 0, r.json()['total'])
    r = get('/api/agents?q=Test')
    check('qidiruv ishlaydi', r.json()['total'] == 1, r.json()['total'])

    r = get(f'/api/agents/{agent.id}')
    check('agent tafsiloti ochiladi', r.status_code == 200, r.status_code)
    check('agent e\'lonlari bilan qaytadi', len(r.json().get('listings', [])) == 1)
    r = get(f'/api/agents/{pending_agent.id}')
    check('tasdiqlanmagan agent tafsiloti 404', r.status_code == 404, r.status_code)

    # ── 2. To'g'ridan-to'g'ri chat ─────────────────────────────────────
    print('\n2) /api/chats/direct/<id> — agent bilan to\'g\'ridan-to\'g\'ri yozishish')
    r = post(f'/api/chats/direct/{agent.id}', {'text': 'Salom, uy bormi?'}, buyer_token)
    check('xaridor agentga yozdi (200)', r.status_code == 200, r.content[:200])
    body = r.json()
    check('xabar saqlandi', len(body.get('items', [])) == 1, body)
    check('thread turi "direct"', body['thread']['kind'] == 'direct', body['thread'].get('kind'))
    check(
        'xaridor uchun suhbatdosh = agent',
        body['thread']['peer_name'] == 'Test Agent', body['thread']['peer_name'],
    )
    thread_id = body['thread']['id']

    r = post(f'/api/chats/direct/{buyer.id}', {'text': 'Ha, bor'}, agent_token)
    check('agent javob yozdi', r.status_code == 200, r.content[:200])
    body = r.json()
    check('AYNAN SHU suhbat ishlatildi (nusxa yaratilmadi)', body['thread']['id'] == thread_id,
          f"{body['thread']['id']} != {thread_id}")
    check('ikkala xabar ham bor', len(body['items']) == 2, len(body['items']))
    check('agent uchun suhbatdosh = xaridor', body['thread']['peer_name'] == 'Xaridor',
          body['thread']['peer_name'])

    r = post(f'/api/chats/direct/{buyer.id}', {'text': 'salom'}, buyer_token)
    check('o\'ziga yozib bo\'lmaydi (400)', r.status_code == 400, r.status_code)
    r = post(f'/api/chats/direct/{agent.id}', {'text': '  '}, buyer_token)
    check('bo\'sh xabar rad etiladi (400)', r.status_code == 400, r.status_code)
    r = post(f'/api/chats/direct/{agent.id}', {'text': 'x' * 2500}, buyer_token)
    check('haddan uzun xabar rad etiladi (400)', r.status_code == 400, r.status_code)
    r = post(f'/api/chats/direct/{agent.id}', {'text': 'salom'})
    check('tokensiz kirish yopiq (401)', r.status_code == 401, r.status_code)

    # ── 3. E'lon chati (eskisi buzilmaganini tekshiramiz) ──────────────
    print('\n3) /api/listings/<id>/chat — e\'lon suhbati (eski oqim)')
    r = post(f'/api/listings/{listing.id}/chat', {'text': 'Bu uy hali bormi?'}, buyer_token)
    check('xaridor e\'lon egasiga yozdi', r.status_code == 200, r.content[:200])
    check('thread turi "listing"', r.json()['thread']['kind'] == 'listing')
    check('suhbatdosh = uy egasi', r.json()['thread']['peer_name'] == 'Uy egasi',
          r.json()['thread']['peer_name'])

    r = get(f'/api/listings/{listing.id}/chat', owner_token)
    check('egasi suhbatlar ro\'yxatini oladi', len(r.json().get('items', [])) == 1)
    check('egasi uchun o\'qilmagan xabar sanaladi', r.json()['items'][0]['unread'] == 1,
          r.json()['items'][0]['unread'])

    r = post(f'/api/listings/{listing.id}/chat?with={buyer.id}', {'text': 'Ha, bor'}, owner_token)
    check('egasi xaridorga javob yozdi', r.status_code == 200, r.content[:200])
    check('suhbatda 2 ta xabar', len(r.json()['items']) == 2, len(r.json()['items']))

    # ── 4. Chat ro'yxati va o'qildi belgisi ────────────────────────────
    print('\n4) /api/me/chats — barcha suhbatlar')
    r = get('/api/me/chats', buyer_token)
    body = r.json()
    kinds = sorted(t['kind'] for t in body['items'])
    check('xaridorda 2 xil suhbat bor', kinds == ['direct', 'listing'], kinds)
    check('o\'qilmagan umumiy soni qaytadi', 'unreadTotal' in body, body.keys())

    r = get(f'/api/chats/{thread_id}', buyer_token)
    check('suhbat ID bo\'yicha ochiladi', r.status_code == 200, r.status_code)
    r = get(f'/api/chats/{thread_id}', owner_token)
    check('begona odam suhbatni ocholmaydi (403)', r.status_code == 403, r.status_code)

    r = get('/api/me/chats', buyer_token)
    direct = [t for t in r.json()['items'] if t['kind'] == 'direct'][0]
    check('ochilgandan keyin o\'qilmagan 0 ga tushdi', direct['unread'] == 0, direct['unread'])

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
