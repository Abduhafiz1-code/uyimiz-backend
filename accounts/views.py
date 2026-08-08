import logging
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from uyimiz.throttling import LoginThrottle, OtpThrottle

from .models import OTPPurpose, PhoneOTP, Role, User, normalize_phone
from .serializers import (
    AdminUserSerializer,
    AgentSerializer,
    AvatarSerializer,
    PasswordLoginSerializer,
    PhoneChangeConfirmSerializer,
    PhoneChangeRequestSerializer,
    SendCodeSerializer,
    UserPublicSerializer,
    VerifyCodeSerializer,
)

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 300
#: Bitta raqamga ketma-ket kod so'rash oralig'i — SMS spamining oldini oladi.
OTP_RESEND_COOLDOWN_SECONDS = 60


def otp_payload(otp, phone):
    """Kod so'ralganda qaytariladigan javob.

    XAVFSIZLIK: kodning o'zi (`demoCode`) faqat DEBUG rejimida qaytariladi.
    Production'da uni javobga qo'shish — istalgan kishi istalgan raqam bilan
    kirishi mumkin degani, chunki kodni SMS kutmasdan javobdan o'qib oladi.
    """
    data = {'ok': True, 'phone': phone, 'expiresInSec': OTP_TTL_SECONDS}
    if settings.DEBUG:
        data['demoCode'] = otp.code
    else:
        # SMS provayder ulanmaguncha kod faqat server logida ko'rinadi.
        logger.info('OTP for %s: %s', phone, otp.code)
    return data


def issue_otp(phone, purpose, reference=''):
    """Yangi kod yaratadi. Avvalgi ishlatilmagan kodlar bekor qilinadi.

    Qaytaradi: (otp, cooldown_qolgan_soniya). Ikkinchisi 0 dan katta bo'lsa —
    kod yaratilmagan, foydalanuvchi biroz kutishi kerak.
    """
    recent = (
        PhoneOTP.objects.filter(phone=phone, purpose=purpose, consumed=False)
        .order_by('-created_at')
        .first()
    )
    if recent and not recent.expired:
        elapsed = (timezone.now() - recent.created_at).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            return None, int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)

    PhoneOTP.objects.filter(phone=phone, purpose=purpose, consumed=False).update(consumed=True)
    otp = PhoneOTP.objects.create(
        phone=phone,
        code=str(random.randint(1000, 9999)),
        purpose=purpose,
        reference=str(reference or ''),
        expires_at=timezone.now() + timedelta(seconds=OTP_TTL_SECONDS),
    )
    return otp, 0


def check_otp(phone, code, purpose, reference=''):
    """Kodni tekshiradi va ishlatilgan deb belgilaydi.

    Qaytaradi: (muvaffaqiyat, xato_kodi). Xato kodlari ilovada tarjima qilinadi.
    """
    otp = (
        PhoneOTP.objects.filter(phone=phone, purpose=purpose, consumed=False)
        .order_by('-created_at')
        .first()
    )
    if otp is None:
        return False, 'code_not_found'
    if otp.locked:
        return False, 'too_many_attempts'
    if otp.expired:
        return False, 'code_expired'
    if reference and otp.reference != str(reference):
        return False, 'wrong_code'
    if otp.code != str(code):
        otp.register_attempt()
        return False, 'wrong_code'
    otp.consume()
    return True, ''


def serializer_for(user):
    if user.role == Role.AGENT:
        return AgentSerializer
    if user.role in (Role.ADMIN, Role.SUPERADMIN):
        return AdminUserSerializer
    return UserPublicSerializer


# ───────────────────────── oddiy foydalanuvchi: OTP orqali ─────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OtpThrottle])
def send_code_view(request):
    """SMS-kod yuboradi.

    Kod DEBUG rejimida javobda (`demoCode`), prod'da esa server logida
    ko'rinadi — SMS provayder ulanmaguncha shunday.
    """
    serializer = SendCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = normalize_phone(serializer.validated_data['phone'])
    if len(phone) < 12:
        return Response({'error': 'invalid_phone'}, status=status.HTTP_400_BAD_REQUEST)

    otp, cooldown = issue_otp(phone, OTPPurpose.LOGIN)
    if otp is None:
        return Response(
            {'error': 'too_soon', 'retryAfterSec': cooldown}, status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    return Response(otp_payload(otp, phone))


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code_view(request):
    """Kodni tasdiqlaydi, kerak bo'lsa yangi 'user' rolli akkaunt yaratadi, token beradi."""
    serializer = VerifyCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = normalize_phone(serializer.validated_data['phone'])

    ok, error = check_otp(phone, serializer.validated_data['code'], OTPPurpose.LOGIN)
    if not ok:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

    user, _created = User.objects.get_or_create(
        phone=phone, defaults={'role': Role.USER, 'name': 'Foydalanuvchi'}
    )
    if not user.is_active:
        return Response({'error': 'account_blocked'}, status=status.HTTP_403_FORBIDDEN)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user': UserPublicSerializer(user, context={'request': request}).data,
    })


# ───────────────────────── agent / admin: telefon + parol ─────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def password_login_view(request):
    """Agent va admin panel uchun bitta login: DRF standart 'Token <key>' sxemasi."""
    serializer = PasswordLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = normalize_phone(serializer.validated_data['phone'])
    user = authenticate(request, phone=phone, password=serializer.validated_data['password'])
    if user is None:
        return Response(
            {'detail': "Telefon raqami yoki parol noto'g'ri"}, status=status.HTTP_400_BAD_REQUEST
        )
    if not user.is_active:
        return Response({'detail': 'Akkaunt bloklangan'}, status=status.HTTP_403_FORBIDDEN)
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {'token': token.key, 'role': user.role, 'user': serializer_for(user)(user).data}
    )


# ───────────────────────── umumiy: barcha rollar uchun ─────────────────────────

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Har qanday rol (user/agent/admin) o'zining profilini shu bitta endpoint orqali oladi."""
    user = request.user
    ser_cls = serializer_for(user)
    ctx = {'request': request}

    if request.method == 'PATCH':
        # Telefon bu yerda o'zgarmaydi — u alohida OTP tasdiqli oqimga ega.
        allowed = {'name', 'email', 'user_kind', 'district', 'avatar_initials'}
        data = {k: v for k, v in request.data.items() if k in allowed}

        if request.data.get('verify') is True:
            user.verified = True
            user.save(update_fields=['verified'])

        if data:
            serializer = ser_cls(user, data=data, partial=True, context=ctx)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            user.refresh_from_db()
    return Response(ser_cls(user, context=ctx).data)


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def avatar_view(request):
    """Profil rasmini yuklash (POST, ``avatar`` fayli) yoki o'chirish (DELETE)."""
    user = request.user
    ctx = {'request': request}

    if request.method == 'DELETE':
        if user.avatar:
            user.avatar.delete(save=False)
        user.avatar = None
        user.save(update_fields=['avatar'])
        return Response(serializer_for(user)(user, context=ctx).data)

    if 'avatar' not in request.FILES:
        return Response({'error': 'no_file'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = AvatarSerializer(user, data={'avatar': request.FILES['avatar']}, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    user.refresh_from_db()
    return Response(serializer_for(user)(user, context=ctx).data)


# ───────────────────────── telefon raqamini o'zgartirish ─────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def phone_change_request_view(request):
    """1-bosqich: yangi raqamga tasdiqlash kodi yuboriladi."""
    serializer = PhoneChangeRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    new_phone = normalize_phone(serializer.validated_data['phone'])

    if len(new_phone) < 12:
        return Response({'error': 'invalid_phone'}, status=status.HTTP_400_BAD_REQUEST)
    if new_phone == request.user.phone:
        return Response({'error': 'same_phone'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(phone=new_phone).exclude(pk=request.user.pk).exists():
        return Response({'error': 'phone_taken'}, status=status.HTTP_400_BAD_REQUEST)

    otp, cooldown = issue_otp(new_phone, OTPPurpose.PHONE_CHANGE, reference=request.user.pk)
    if otp is None:
        return Response(
            {'error': 'too_soon', 'retryAfterSec': cooldown}, status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    return Response(otp_payload(otp, new_phone))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def phone_change_confirm_view(request):
    """2-bosqich: kod to'g'ri bo'lsa raqam almashtiriladi."""
    serializer = PhoneChangeConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    new_phone = normalize_phone(serializer.validated_data['phone'])
    user = request.user

    if User.objects.filter(phone=new_phone).exclude(pk=user.pk).exists():
        return Response({'error': 'phone_taken'}, status=status.HTTP_400_BAD_REQUEST)

    ok, error = check_otp(
        new_phone, serializer.validated_data['code'], OTPPurpose.PHONE_CHANGE, reference=user.pk
    )
    if not ok:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

    user.phone = new_phone
    user.save(update_fields=['phone'])
    return Response(serializer_for(user)(user, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response({'ok': True})
