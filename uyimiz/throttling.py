"""So'rov cheklovlari (throttling).

Nega ScopedRateThrottle emas: u scope'ni view'dagi `throttle_scope`
atributidan o'qiydi va topa olmasa **hech qanday cheklovsiz o'tkazib
yuboradi** — funksiya-view'larda `@throttle_classes([...])` bilan
ishlatilganda aynan shunday bo'ladi va cheklov jimgina ishlamay qoladi.

SimpleRateThrottle esa scope'ni klassning o'zidan oladi, shuning uchun
ishonchli. Tezlik `settings.DEFAULT_THROTTLE_RATES` dan olinadi.
"""

from rest_framework.throttling import SimpleRateThrottle


class _IdentThrottle(SimpleRateThrottle):
    """Kirgan foydalanuvchini id bo'yicha, mehmonni IP bo'yicha cheklaydi."""

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            ident = f'user-{user.pk}'
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class OtpThrottle(_IdentThrottle):
    """Kirish uchun SMS-kod so'rash (settings: THROTTLE_OTP)."""

    scope = 'otp'


class LoginThrottle(_IdentThrottle):
    """Parol bilan kirishga urinish (settings: THROTTLE_LOGIN)."""

    scope = 'login'


class SignThrottle(_IdentThrottle):
    """Shartnoma imzo kodini so'rash (settings: THROTTLE_SIGN)."""

    scope = 'sign'
