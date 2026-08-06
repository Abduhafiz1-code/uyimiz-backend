from rest_framework import serializers

from accounts.models import AdminTitle, CertificationStatus, Role, User
from listings.models import Listing

from .models import AuditLog, ModerationItem, PlatformSettings, Tariff


class AdminUserRowSerializer(serializers.ModelSerializer):
    """/api/admin/users — barcha rollardagi foydalanuvchilar bitta jadvalda."""

    type = serializers.SerializerMethodField()
    status = serializers.CharField(source='status_label', read_only=True)
    since = serializers.DateTimeField(source='date_joined', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'phone', 'role', 'user_kind', 'type', 'status', 'is_active', 'verified', 'since']
        read_only_fields = ['id', 'since']

    def get_type(self, obj):
        if obj.role == Role.AGENT:
            return 'Agent'
        return dict(User._meta.get_field('user_kind').choices).get(obj.user_kind, 'Foydalanuvchi')


class AdminAgentRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'name', 'phone', 'district', 'rating', 'total_deals',
            'commission_rate', 'certification', 'tier', 'is_active',
        ]
        read_only_fields = ['id', 'rating', 'total_deals', 'tier']


class AdminListingRowSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.name', read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'district', 'address', 'deal', 'price', 'currency', 'status', 'badge',
            'owner', 'owner_name', 'verified', 'created_at',
        ]
        read_only_fields = ['id', 'owner_name', 'created_at']


class ModerationItemSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.address', read_only=True)
    listing_district = serializers.CharField(source='listing.district', read_only=True)

    class Meta:
        model = ModerationItem
        fields = ['id', 'listing', 'listing_title', 'listing_district', 'reason', 'score', 'created_at']
        read_only_fields = ['id', 'listing_title', 'listing_district', 'created_at']


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ['id', 'name', 'price_label', 'period', 'description', 'order']
        read_only_fields = ['id']


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = [
            'ai_threshold', 'deal_commission_percent', 'contract_price', 'vip_price',
            'premium_post_price', 'agent_commission_percent', 'platform_share_percent',
            'agent_subscription_price', 'stage',
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    admin_name = serializers.CharField(source='admin_label', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'admin_name', 'action', 'object_label', 'created_at']


class AdminAccountSerializer(serializers.ModelSerializer):
    """/api/admin/admins — platforma administratorlarini boshqarish (Superadmin/Admin/Moderator)."""

    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'phone', 'admin_title', 'is_active', 'date_joined', 'password']
        read_only_fields = ['id', 'date_joined']

    def create(self, validated_data):
        password = validated_data.pop('password', None) or User.objects.make_random_password()
        validated_data['role'] = Role.ADMIN
        validated_data.setdefault('admin_title', AdminTitle.ADMIN)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
