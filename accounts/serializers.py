from rest_framework import serializers

from .models import User


class UserPublicSerializer(serializers.ModelSerializer):
    """Asosiy ilova uchun — oddiy foydalanuvchi profili (parol/rol yashirin)."""

    initials = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    user_kind_label = serializers.CharField(source='get_user_kind_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'name', 'email', 'verified', 'user_kind', 'user_kind_label',
            'district', 'initials', 'avatar_url', 'date_joined',
        ]
        # Telefon shu yerdan emas, alohida OTP tasdiqli oqim orqali o'zgaradi.
        read_only_fields = ['id', 'phone', 'verified', 'date_joined']

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url


class AgentPublicSerializer(serializers.ModelSerializer):
    """Ommaviy agentlar katalogi uchun (sayt va mobil ilovaning "Agentlar" bo'limi).

    Faqat ADMIN TASDIQLAGAN agentlar shu serializer orqali ko'rsatiladi.
    Telefon raqami ataylab qaytariladi — foydalanuvchi agentga qo'ng'iroq
    qila olishi kerak; qolgan ichki maydonlar (komissiya, platforma ulushi)
    bu yerda YO'Q, ular faqat CRM va admin panelga tegishli.
    """

    initials = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    deals = serializers.IntegerField(source='total_deals', read_only=True)
    years = serializers.SerializerMethodField()
    top = serializers.SerializerMethodField()
    listings_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'name', 'phone', 'district', 'initials', 'avatar_url',
            'rating', 'rating_count', 'tier', 'deals', 'years', 'top',
            'avg_response_minutes', 'listings_count', 'date_joined',
        ]

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    def get_years(self, obj):
        """Platformada necha yildan beri — ro'yxatdan o'tgan sanadan hisoblanadi."""
        from django.utils import timezone

        if not obj.date_joined:
            return 0
        days = (timezone.now() - obj.date_joined).days
        return max(0, days // 365)

    def get_top(self, obj):
        return obj.tier in ('Tajribali', 'Top')

    def get_listings_count(self, obj):
        # `annotate` bilan kelgan bo'lsa qo'shimcha so'rov qilinmaydi.
        value = getattr(obj, 'active_listings', None)
        if value is not None:
            return value
        return obj.agent_listings.filter(status='active').count()


class AgentSerializer(serializers.ModelSerializer):
    """Agent CRM uchun — reyting, daraja, sertifikat holati bilan."""

    initials = serializers.CharField(read_only=True)
    tier_percent = serializers.SerializerMethodField()
    tier_remaining = serializers.SerializerMethodField()
    tier_next_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'name', 'email', 'district', 'initials',
            'rating', 'rating_count', 'tier', 'certification', 'platform_share',
            'commission_rate', 'avg_response_minutes', 'total_deals', 'date_joined',
            'tier_percent', 'tier_remaining', 'tier_next_label',
        ]
        read_only_fields = ['id', 'phone', 'rating', 'tier', 'total_deals', 'date_joined', 'certification']

    def _progress(self, obj):
        if not hasattr(obj, '_cached_progress'):
            obj._cached_progress = obj.tier_progress()
        return obj._cached_progress

    def get_tier_percent(self, obj):
        return self._progress(obj)[0]

    def get_tier_remaining(self, obj):
        return self._progress(obj)[1]

    def get_tier_next_label(self, obj):
        return self._progress(obj)[2]


class AdminUserSerializer(serializers.ModelSerializer):
    """Admin panel uchun — istalgan roldagi foydalanuvchini to'liq ko'rsatadi."""

    status = serializers.CharField(source='status_label', read_only=True)
    type = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'name', 'email', 'role', 'user_kind', 'type', 'district',
            'verified', 'is_active', 'status', 'rating', 'tier', 'certification',
            'admin_title', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']

    def get_type(self, obj):
        if obj.role == 'agent':
            return 'Agent'
        if obj.role in ('admin', 'superadmin'):
            return obj.admin_title or 'Admin'
        return dict(User._meta.get_field('user_kind').choices).get(obj.user_kind, 'Foydalanuvchi')


class SendCodeSerializer(serializers.Serializer):
    phone = serializers.CharField()


class VerifyCodeSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()


class PasswordLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})


class PhoneChangeRequestSerializer(serializers.Serializer):
    """1-bosqich: yangi raqamga kod yuborish."""

    phone = serializers.CharField()


class PhoneChangeConfirmSerializer(serializers.Serializer):
    """2-bosqich: yangi raqamga kelgan kodni tasdiqlash."""

    phone = serializers.CharField()
    code = serializers.CharField()


class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['avatar']


class AgentApplySerializer(serializers.Serializer):
    """Uyimiz Agent bo'lish uchun ariza.

    Foydalanuvchi avval SMS-kod bilan kirgan bo'lishi kerak — shuning
    uchun bu yerda telefon so'ralmaydi, u tokendan olinadi.
    """

    name = serializers.CharField(max_length=150)
    district = serializers.CharField(max_length=64)
    email = serializers.EmailField(required=False, allow_blank=True)
    historical_deals = serializers.IntegerField(
        required=False, min_value=0, max_value=10000,
        help_text='Platformadan tashqarida yopgan bitimlari soni',
    )

    def validate_name(self, v):
        v = v.strip()
        if len(v) < 3:
            raise serializers.ValidationError("Ism kamida 3 ta harfdan iborat bo'lsin")
        return v

    def validate_district(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError('Hududni tanlang')
        return v
