from rest_framework import serializers

from .models import ChatMessage, ChatThread, Contract, Favorite, Listing, ListingPhoto


class ListingPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPhoto
        fields = ['id', 'image', 'order', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            data['image'] = instance.image.url
        return data


class ListingSerializer(serializers.ModelSerializer):
    photos = ListingPhotoSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source='owner.name', read_only=True)
    owner_phone = serializers.CharField(source='owner.phone', read_only=True)
    owner_verified = serializers.BooleanField(source='owner.verified', read_only=True)
    agent_name = serializers.CharField(source='agent.name', read_only=True, default=None)
    by_agent = serializers.BooleanField(read_only=True)
    promoted = serializers.BooleanField(read_only=True)
    is_new = serializers.BooleanField(read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'deal', 'district', 'address', 'price', 'currency', 'rooms', 'area',
            'floor', 'floors', 'year', 'ptype', 'repair', 'docs', 'features',
            'verified', 'contract_ready', 'status', 'badge', 'promoted', 'promoted_until',
            'is_new', 'by_agent', 'rating_avg', 'rating_count', 'views', 'description',
            'owner', 'owner_name', 'owner_phone', 'owner_verified',
            'agent', 'agent_name', 'photos', 'is_favorite', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'badge', 'promoted', 'promoted_until', 'verified',
            'rating_avg', 'rating_count', 'views', 'owner', 'agent', 'photos', 'created_at', 'updated_at',
        ]

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        favs = self.context.get('favorite_ids')
        if favs is not None:
            return obj.id in favs
        return Favorite.objects.filter(user=request.user, listing=obj).exists()


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'thread', 'sender', 'sender_name', 'text', 'created_at', 'read_at']
        read_only_fields = ['id', 'thread', 'sender', 'sender_name', 'created_at', 'read_at']


class ChatThreadSerializer(serializers.ModelSerializer):
    """Chat ro'yxatidagi bitta qator.

    Muhim: ``peer_*`` maydonlari SO'ROV YUBORGAN foydalanuvchiga qarab
    hisoblanadi — ya'ni har kim suhbatdoshining ismini ko'radi, o'zinikini
    emas. Ilgari faqat ``buyer_name`` qaytardi va e'lon egasi o'z chat
    ro'yxatida hamma joyda xaridorning ismini ko'rar, xaridor esa o'z
    ismini ko'rardi.
    """

    listing_title = serializers.CharField(source='listing.address', read_only=True, default='')
    listing_district = serializers.CharField(source='listing.district', read_only=True, default='')
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    kind = serializers.SerializerMethodField()
    peer_id = serializers.SerializerMethodField()
    peer_name = serializers.SerializerMethodField()
    peer_role = serializers.SerializerMethodField()
    peer_avatar = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = [
            'id', 'kind', 'listing', 'listing_title', 'listing_district',
            'buyer', 'buyer_name', 'recipient',
            'peer_id', 'peer_name', 'peer_role', 'peer_avatar',
            'created_at', 'updated_at', 'last_message', 'unread',
        ]

    # ── suhbatdoshni aniqlash ────────────────────────────────────────────
    def _me(self):
        request = self.context.get('request')
        return getattr(request, 'user', None)

    def _peer(self, obj):
        if not hasattr(obj, '_peer_cache'):
            me = self._me()
            obj._peer_cache = obj.other_party(me) if me and me.is_authenticated else obj.buyer
        return obj._peer_cache

    def get_kind(self, obj):
        return 'listing' if obj.listing_id else 'direct'

    def get_peer_id(self, obj):
        peer = self._peer(obj)
        return peer.id if peer else None

    def get_peer_name(self, obj):
        peer = self._peer(obj)
        return peer.name if peer else ''

    def get_peer_role(self, obj):
        peer = self._peer(obj)
        return peer.role if peer else ''

    def get_peer_avatar(self, obj):
        peer = self._peer(obj)
        if not peer or not peer.avatar:
            return None
        request = self.context.get('request')
        url = peer.avatar.url
        return request.build_absolute_uri(url) if request else url

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        return ChatMessageSerializer(msg).data if msg else None

    def get_unread(self, obj):
        """Menga yozilgan, hali o'qilmagan xabarlar soni."""
        me = self._me()
        if not me or not me.is_authenticated:
            return 0
        return obj.messages.filter(read_at__isnull=True).exclude(sender_id=me.id).count()


class ContractSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.name', read_only=True)
    seller_phone = serializers.CharField(source='seller.phone', read_only=True)
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    buyer_phone = serializers.CharField(source='buyer.phone', read_only=True)
    listing_address = serializers.CharField(source='listing.address', read_only=True)
    listing_district = serializers.CharField(source='listing.district', read_only=True)
    listing_area = serializers.DecimalField(
        source='listing.area', max_digits=7, decimal_places=1, read_only=True
    )
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    #: Ilova shu ikki bayroqqa qarab qaysi tugmani ko'rsatishni hal qiladi.
    my_role = serializers.SerializerMethodField()
    can_sign = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id', 'listing', 'listing_address', 'listing_district', 'listing_area',
            'seller', 'seller_name', 'seller_phone', 'buyer', 'buyer_name', 'buyer_phone',
            'agent', 'deal', 'price', 'currency', 'service_fee', 'seller_signed', 'buyer_signed',
            'status', 'status_label', 'my_role', 'can_sign', 'cancel_reason',
            'pdf_url', 'created_at', 'seller_approved_at', 'signed_at',
        ]
        read_only_fields = [
            'id', 'seller', 'buyer', 'agent', 'seller_signed', 'buyer_signed',
            'status', 'pdf_url', 'created_at', 'seller_approved_at', 'signed_at',
        ]

    def _user(self):
        request = self.context.get('request')
        return getattr(request, 'user', None)

    def get_my_role(self, obj):
        user = self._user()
        if user is None or not user.is_authenticated:
            return None
        if user.id == obj.seller_id:
            return 'seller'
        if user.id == obj.buyer_id:
            return 'buyer'
        return None

    def get_can_sign(self, obj):
        user = self._user()
        return bool(
            user
            and user.is_authenticated
            and user.id == obj.buyer_id
            and obj.seller_signed
            and obj.status == 'awaiting_sign'
        )

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        if obj.pdf and hasattr(obj.pdf, 'url'):
            return request.build_absolute_uri(obj.pdf.url) if request else obj.pdf.url
        return None
