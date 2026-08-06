import random
from datetime import timedelta

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import PhoneOTP, Role, User, normalize_phone
from .serializers import (
    AdminUserSerializer,
    AgentSerializer,
    PasswordLoginSerializer,
    SendCodeSerializer,
    UserPublicSerializer,
    VerifyCodeSerializer,
)

OTP_TTL_SECONDS = 300


def serializer_for(user):
    if user.role == Role.AGENT:
        return AgentSerializer
    if user.role in (Role.ADMIN, Role.SUPERADMIN):
        return AdminUserSerializer
    return UserPublicSerializer


# ───────────────────────── oddiy foydalanuvchi: OTP orqali ─────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def send_code_view(request):
    """SMS-kod yuboradi (DEMO: real SMS integratsiyasi o'rniga javobning o'zida qaytadi)."""
    serializer = SendCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = normalize_phone(serializer.validated_data['phone'])
    if len(phone) < 12:
        return Response({'error': 'invalid_phone'}, status=status.HTTP_400_BAD_REQUEST)

    code = str(random.randint(1000, 9999))
    PhoneOTP.objects.create(
        phone=phone, code=code, expires_at=timezone.now() + timedelta(seconds=OTP_TTL_SECONDS)
    )
    return Response({'ok': True, 'phone': phone, 'demoCode': code, 'expiresInSec': OTP_TTL_SECONDS})


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code_view(request):
    """Kodni tasdiqlaydi, kerak bo'lsa yangi 'user' rolli akkaunt yaratadi, token beradi."""
    serializer = VerifyCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = normalize_phone(serializer.validated_data['phone'])
    code = str(serializer.validated_data['code'])

    otp = PhoneOTP.objects.filter(phone=phone, consumed=False).order_by('-created_at').first()
    if not otp or not otp.is_valid(code):
        return Response({'error': 'wrong_code'}, status=status.HTTP_400_BAD_REQUEST)
    otp.consumed = True
    otp.save(update_fields=['consumed'])

    user, _created = User.objects.get_or_create(
        phone=phone, defaults={'role': Role.USER, 'name': 'Foydalanuvchi'}
    )
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserPublicSerializer(user).data})


# ───────────────────────── agent / admin: telefon + parol ─────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
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
    if request.method == 'PATCH':
        allowed = {'name', 'email', 'district'} if user.role != Role.USER else {'name', 'email'}
        data = {k: v for k, v in request.data.items() if k in allowed}
        if request.data.get('verify') is True and user.role == Role.USER:
            user.verified = True
            user.save(update_fields=['verified'])
        serializer = ser_cls(user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ser_cls(user).data)
    return Response(ser_cls(user).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response({'ok': True})
