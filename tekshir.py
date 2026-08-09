#!/usr/bin/env python3
"""Uyimiz.uz backend diagnostikasi.

Jonli serverni tekshiradi va nima ishlamayotganini o'zbekcha aytadi.
Hech qanday kutubxona kerak emas — faqat Python.

Ishlatish:
    python tekshir.py
    python tekshir.py http://127.0.0.1:8000      # lokal backendni tekshirish
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'https://uyimiz-backend.onrender.com').rstrip('/')

OK = '  [OK]  '
XATO = '  [XATO]'
OGOH = '  [!]   '


def so_rov(path, method='GET', body=None, token=None, timeout=90):
    """Bitta so'rov yuboradi. Qaytaradi: (status, json_yoki_matn, sekund)."""
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    if token:
        req.add_header('Authorization', f'Token {token}')

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8', 'replace')
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        status = e.code
    except Exception as e:  # noqa: BLE001
        return 0, str(e), time.time() - t0

    try:
        return status, json.loads(raw), time.time() - t0
    except json.JSONDecodeError:
        return status, raw, time.time() - t0


def main():
    print(f'\nTekshirilmoqda: {BASE}\n' + '─' * 60)

    # ── 1. Server javob beradimi ──
    print('\n1. Server javob beradimi')
    status, body, sek = so_rov('/api/health')

    if status == 0:
        print(f'{XATO} Serverga umuman ulanib bo\'lmadi.')
        print(f'        Sabab: {body}')
        print('\n        Tekshiring:')
        print('        • Render dashboard\'da servis "Live" holatdami?')
        print('        • Manzil to\'g\'rimi? (https:// bilan boshlanishi kerak)')
        return 1

    if sek > 20:
        print(f'{OGOH} Javob {sek:.0f} soniyada keldi — server uyqudan turdi.')
        print('        Bu Free plan xususiyati. Starter ($7/oy) uxlamaydi.')
    else:
        print(f'{OK} Javob berdi ({sek:.1f}s)')

    if status != 200:
        print(f'{XATO} /api/health {status} qaytardi (200 bo\'lishi kerak).')
        print(f'        Javob: {str(body)[:300]}')
        if status == 502 or status == 503:
            print('\n        Bu odatda konteyner ishga tushmaganini bildiradi.')
            print('        Render → Logs bo\'limini oching va xatoni ko\'ring.')
        return 1

    if not isinstance(body, dict):
        print(f'{XATO} Javob JSON emas — eski kod ishlayotgan bo\'lishi mumkin.')
        print('        Yangi kodni push qilib, qayta deploy qiling.')
        return 1

    # ── 2. Backend o'zi haqida nima deydi ──
    print('\n2. Backend sozlamalari')
    print(f'        DEBUG rejimi   : {body.get("debug")}')
    print(f'        Baza           : {body.get("database")}')
    print(f'        Bazaga ulandi  : {body.get("databaseConnected")}')
    print(f'        Migratsiyalar  : {body.get("pendingMigrations", "?")} ta kutmoqda')
    print(f'        SMS test rejimi: {body.get("otpTestMode")}')
    print(f'        Media          : {body.get("mediaStorage")}')

    muammolar = body.get('problems') or []
    if muammolar:
        print('\n3. Topilgan muammolar')
        for m in muammolar:
            print(f'{OGOH} {m}')
    else:
        print('\n3. Muammo topilmadi')

    # ── 4. Ma'lumot o'qiladimi ──
    print('\n4. API ishlayaptimi')
    for nom, yol in [("tumanlar", '/api/districts'), ("e'lonlar", '/api/listings/?perPage=1')]:
        st, bd, _ = so_rov(yol)
        if st == 200:
            n = len(bd.get('items', [])) if isinstance(bd, dict) else 0
            print(f'{OK} {nom}: {st} ({n} ta yozuv)')
        else:
            print(f'{XATO} {nom}: {st}')
            if st == 500:
                print('        500 = jadvallar yo\'q. Migratsiya bajarilmagan.')

    # ── 5. Ro'yxatdan o'tish ishlaydimi ──
    print('\n5. Kirish (signup/login) ishlayaptimi')
    # Ataylab hech qayerda ishlatilmaydigan raqam — seed_demo'dagi
    # admin/agent hisoblariga tegib ketmasligi uchun.
    telefon = '+998900000099'
    st, bd, _ = so_rov('/api/auth/send-code', 'POST', {'phone': telefon})

    if st == 429:
        print(f'{OGOH} Cheklovga tushdi (429) — bir oz kutib qayta urinib ko\'ring.')
    elif st != 200:
        print(f'{XATO} Kod yuborilmadi: {st} — {str(bd)[:200]}')
    else:
        kod = bd.get('demoCode') if isinstance(bd, dict) else None
        if not kod:
            print(f'{OGOH} Kod yuborildi, lekin javobda ko\'rsatilmadi.')
            print('        OTP_TEST_MODE=1 qo\'ysangiz kod javobda qaytadi')
            print('        va SMS provaydersiz sinab ko\'rasiz.')
        else:
            print(f'{OK} Kod keldi: {kod}')
            st2, bd2, _ = so_rov('/api/auth/verify', 'POST', {'phone': telefon, 'code': kod})
            if st2 == 200 and isinstance(bd2, dict) and bd2.get('token'):
                token = bd2['token']
                print(f'{OK} Kirish muvaffaqiyatli, token olindi')
                st3, bd3, _ = so_rov('/api/auth/me', token=token)
                if st3 == 200:
                    ism = bd3.get('name') if isinstance(bd3, dict) else '?'
                    print(f'{OK} Profil o\'qildi: {ism}')
                else:
                    print(f'{XATO} Profil o\'qilmadi: {st3}')
                    print('        Token ishlamayapti — Authorization sarlavhasi muammosi.')
            else:
                print(f'{XATO} Kod tasdiqlanmadi: {st2} — {str(bd2)[:200]}')

    # ── 6. CORS ──
    print('\n6. CORS (brauzerdan ulanish)')
    req = urllib.request.Request(f'{BASE}/api/auth/me', method='OPTIONS')
    req.add_header('Origin', 'https://uyimiz.vercel.app')
    req.add_header('Access-Control-Request-Method', 'GET')
    req.add_header('Access-Control-Request-Headers', 'authorization')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            allow_origin = r.headers.get('access-control-allow-origin')
            allow_headers = (r.headers.get('access-control-allow-headers') or '').lower()
        if allow_origin and 'authorization' in allow_headers:
            print(f'{OK} Ruxsat bor (origin: {allow_origin})')
        else:
            print(f'{XATO} CORS to\'liq sozlanmagan.')
            print(f'        allow-origin: {allow_origin}')
            print(f'        allow-headers: {allow_headers}')
            print('        Brauzerdagi sayt backendga ulana olmaydi.')
    except Exception as e:  # noqa: BLE001
        print(f'{XATO} Preflight so\'rovi ishlamadi: {e}')

    print('\n' + '─' * 60)
    holat = body.get('status')
    if holat == 'error':
        print('XULOSA: jiddiy muammo bor — yuqoridagi ro\'yxatga qarang.\n')
        return 1
    if holat == 'warning':
        print('XULOSA: ishlayapti, lekin e\'tibor talab qiladigan joylari bor.\n')
        return 0
    print('XULOSA: hammasi joyida.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
