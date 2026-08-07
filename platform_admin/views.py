from django.db.models import Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from accounts.models import CertificationStatus, Role, User
from accounts.permissions import IsAdminRole, IsSuperAdmin
from crm.models import Deal, DealStage
from listings.models import Listing, ListingStatus

from .models import AuditLog, ModerationItem, PlatformSettings, Tariff, log_action
from .serializers import (
    AdminAccountSerializer,
    AdminAgentRowSerializer,
    AdminListingRowSerializer,
    AdminUserRowSerializer,
    AuditLogSerializer,
    ModerationItemSerializer,
    PlatformSettingsSerializer,
    TariffSerializer,
)


class AdminUserViewSet(viewsets.ModelViewSet):
    """/api/admin/users — istalgan roldagi (user/agent) akkauntlarni boshqaradi."""

    permission_classes = [IsAdminRole]
    # Admin panel jadvallari to'liq ro'yxat bilan ishlaydi (filtr/qidiruv brauzer tomonida),
    # shuning uchun bu yerda sahifalash o'chirilgan.
    pagination_class = None
    serializer_class = AdminUserRowSerializer
    queryset = User.objects.filter(role__in=[Role.USER, Role.AGENT]).order_by('-date_joined')

    def get_queryset(self):
        qs = super().get_queryset()
        if role := self.request.query_params.get('role'):
            qs = qs.filter(role=role)
        if kind := self.request.query_params.get('user_kind'):
            qs = qs.filter(user_kind=kind)
        return qs

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(self.request.user, "Foydalanuvchi qo'shildi", user.name)

    def perform_update(self, serializer):
        user = serializer.save()
        log_action(self.request.user, "Foydalanuvchi ma'lumotlari yangilandi", user.name)

    def perform_destroy(self, instance):
        log_action(self.request.user, "Foydalanuvchi o'chirildi", instance.name)
        instance.delete()

    @action(detail=True, methods=['patch'], url_path='toggle-block')
    def toggle_block(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        log_action(
            request.user,
            'Foydalanuvchi bloklandi' if not user.is_active else 'Foydalanuvchi faollashtirildi',
            user.name,
        )
        return Response(self.get_serializer(user).data)


class AdminAgentViewSet(viewsets.ModelViewSet):
    """/api/admin/agents — Uyimiz Agent sertifikatlash va nazorat (docx 5-band)."""

    permission_classes = [IsAdminRole]
    # Admin panel jadvallari to'liq ro'yxat bilan ishlaydi (filtr/qidiruv brauzer tomonida),
    # shuning uchun bu yerda sahifalash o'chirilgan.
    pagination_class = None
    serializer_class = AdminAgentRowSerializer
    queryset = User.objects.filter(role=Role.AGENT).order_by('-rating')

    def perform_create(self, serializer):
        agent = serializer.save(role=Role.AGENT)
        agent.set_unusable_password()
        agent.save()
        log_action(self.request.user, "Agent qo'shildi", agent.name)

    def perform_update(self, serializer):
        agent = serializer.save()
        log_action(self.request.user, "Agent ma'lumotlari yangilandi", agent.name)

    def _set_cert(self, request, pk, cert, label):
        agent = self.get_object()
        agent.certification = cert
        agent.save(update_fields=['certification'])
        log_action(request.user, label, agent.name)
        return Response(self.get_serializer(agent).data)

    @action(detail=True, methods=['patch'])
    def approve(self, request, pk=None):
        return self._set_cert(request, pk, CertificationStatus.TASDIQLANGAN, 'Agent sertifikatlandi')

    @action(detail=True, methods=['patch'])
    def reject(self, request, pk=None):
        return self._set_cert(request, pk, CertificationStatus.RAD, 'Agent sertifikati rad etildi')

    @action(detail=True, methods=['patch'])
    def revoke(self, request, pk=None):
        return self._set_cert(request, pk, CertificationStatus.BEKOR, 'Sertifikat bekor qilindi')

    def perform_destroy(self, instance):
        log_action(self.request.user, "Agent o'chirildi", instance.name)
        instance.delete()


class AdminListingViewSet(viewsets.ModelViewSet):
    """/api/admin/posts — barcha e'lonlar ustidan to'liq nazorat."""

    permission_classes = [IsAdminRole]
    # Admin panel jadvallari to'liq ro'yxat bilan ishlaydi (filtr/qidiruv brauzer tomonida),
    # shuning uchun bu yerda sahifalash o'chirilgan.
    pagination_class = None
    serializer_class = AdminListingRowSerializer
    queryset = Listing.objects.select_related('owner').order_by('-created_at')

    def get_queryset(self):
        qs = super().get_queryset()
        if status_filter := self.request.query_params.get('status'):
            qs = qs.filter(status=status_filter)
        if deal := self.request.query_params.get('deal'):
            qs = qs.filter(deal=deal)
        return qs

    def perform_create(self, serializer):
        listing = serializer.save()
        log_action(self.request.user, "E'lon qo'shildi", f'ID {listing.id}')

    def perform_update(self, serializer):
        listing = serializer.save()
        log_action(self.request.user, "E'lon yangilandi", f'ID {listing.id}')

    def perform_destroy(self, instance):
        log_action(self.request.user, "E'lon o'chirildi", f'ID {instance.id}')
        instance.delete()

    @action(detail=True, methods=['patch'])
    def approve(self, request, pk=None):
        listing = self.get_object()
        listing.status = ListingStatus.ACTIVE
        listing.verified = True
        listing.save(update_fields=['status', 'verified'])
        ModerationItem.objects.filter(listing=listing).delete()
        log_action(request.user, "E'lon tasdiqlandi", f'ID {listing.id}')
        return Response(self.get_serializer(listing).data)

    @action(detail=True, methods=['patch'])
    def reject(self, request, pk=None):
        listing = self.get_object()
        listing.status = ListingStatus.REJECTED
        listing.save(update_fields=['status'])
        ModerationItem.objects.filter(listing=listing).delete()
        log_action(request.user, "E'lon rad etildi", f'ID {listing.id}')
        return Response(self.get_serializer(listing).data)


class ModerationViewSet(viewsets.ModelViewSet):
    """/api/admin/moderation — AI-shubhali e'lonlar navbati (docx 3-bosqich)."""

    permission_classes = [IsAdminRole]
    # Admin panel jadvallari to'liq ro'yxat bilan ishlaydi (filtr/qidiruv brauzer tomonida),
    # shuning uchun bu yerda sahifalash o'chirilgan.
    pagination_class = None
    serializer_class = ModerationItemSerializer
    queryset = ModerationItem.objects.select_related('listing').order_by('-created_at')

    @action(detail=True, methods=['patch'])
    def approve(self, request, pk=None):
        item = self.get_object()
        item.listing.status = ListingStatus.ACTIVE
        item.listing.verified = True
        item.listing.save(update_fields=['status', 'verified'])
        log_action(request.user, "E'lon tasdiqlandi", f'ID {item.listing_id}')
        item.delete()
        return Response({'ok': True})

    @action(detail=True, methods=['patch'])
    def reject(self, request, pk=None):
        item = self.get_object()
        item.listing.status = ListingStatus.REJECTED
        item.listing.save(update_fields=['status'])
        log_action(request.user, "E'lon rad etildi", f'ID {item.listing_id}')
        item.delete()
        return Response({'ok': True})


class TariffViewSet(viewsets.ModelViewSet):
    """/api/admin/tariffs — Premium/VIP/shartnoma/agent obunasi narxlari (docx 4-band)."""

    permission_classes = [IsAdminRole]
    # Admin panel jadvallari to'liq ro'yxat bilan ishlaydi (filtr/qidiruv brauzer tomonida),
    # shuning uchun bu yerda sahifalash o'chirilgan.
    pagination_class = None
    serializer_class = TariffSerializer
    queryset = Tariff.objects.all()

    def perform_update(self, serializer):
        tariff = serializer.save()
        log_action(self.request.user, 'Tarif narxi yangilandi', tariff.name)


class AdminAccountViewSet(viewsets.ModelViewSet):
    """/api/admin/admins — faqat Superadmin platforma administratorlarini boshqaradi."""

    permission_classes = [IsSuperAdmin]
    pagination_class = None
    serializer_class = AdminAccountSerializer
    queryset = User.objects.filter(role__in=[Role.ADMIN, Role.SUPERADMIN]).order_by('id')

    def perform_create(self, serializer):
        admin = serializer.save()
        log_action(self.request.user, "Admin qo'shildi", admin.name)

    def perform_update(self, serializer):
        admin = serializer.save()
        log_action(self.request.user, "Admin ma'lumotlari yangilandi", admin.name)

    def perform_destroy(self, instance):
        if instance.admin_title == 'Superadmin':
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Superadminni o'chirib bo'lmaydi")
        log_action(self.request.user, "Admin o'chirildi", instance.name)
        instance.delete()


@api_view(['GET'])
@permission_classes([IsAdminRole])
def audit_view(request):
    if request.method == 'GET':
        items = AuditLog.objects.all()[:200]
        return Response(AuditLogSerializer(items, many=True).data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAdminRole])
def settings_view(request):
    row = PlatformSettings.load()
    if request.method == 'PUT':
        before = PlatformSettingsSerializer(row).data
        serializer = PlatformSettingsSerializer(row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        for field, new_value in serializer.validated_data.items():
            if before.get(field) != new_value:
                log_action(request.user, f'Sozlama yangilandi: {field}', str(new_value))
        return Response(PlatformSettingsSerializer(row).data)
    return Response(PlatformSettingsSerializer(row).data)


@api_view(['GET'])
@permission_classes([IsAdminRole])
def dashboard_view(request):
    today = timezone.now().date()
    users_total = User.objects.filter(role=Role.USER).count()
    active_agents = User.objects.filter(role=Role.AGENT, certification=CertificationStatus.TASDIQLANGAN).count()
    posts_today = Listing.objects.filter(created_at__date=today).count()
    moderation_count = ModerationItem.objects.count()
    posts_total = Listing.objects.count()
    deals_total = Deal.objects.filter(stage=DealStage.YOPILGAN).count()
    settings_row = PlatformSettings.load()
    return Response({
        'usersTotal': users_total,
        'activeAgents': active_agents,
        'postsToday': posts_today,
        'moderationCount': moderation_count,
        'postsTotal': posts_total,
        'dealsTotal': deals_total,
        'stage': settings_row.stage,
    })
