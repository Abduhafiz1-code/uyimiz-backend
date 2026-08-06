from rest_framework import serializers

from .models import Activity, Client, Deal, Property, PropertyPhoto, Showing


class ClientSerializer(serializers.ModelSerializer):
    initials = serializers.CharField(read_only=True)
    deals_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'phone', 'request', 'deal_type', 'district', 'budget_label',
            'budget_min', 'budget_max', 'status', 'source', 'note', 'is_verified',
            'initials', 'deals_count', 'created_at', 'last_contact_at',
        ]
        read_only_fields = ['id', 'initials', 'deals_count']

    def get_deals_count(self, obj):
        return obj.deals.count()


class PropertyPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyPhoto
        fields = ['id', 'image', 'order', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            data['image'] = instance.image.url
        return data


class PropertySerializer(serializers.ModelSerializer):
    price_label = serializers.CharField(read_only=True)
    photos = PropertyPhotoSerializer(many=True, read_only=True)
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'public_listing', 'photos', 'cover', 'listing_id', 'title', 'district', 'address',
            'deal_type', 'price', 'price_label', 'currency', 'rooms', 'area', 'floor', 'total_floors',
            'built_year', 'status', 'badge', 'is_verified', 'owner_name', 'owner_phone',
            'photo_count', 'views', 'description', 'created_at',
        ]
        read_only_fields = ['id', 'price_label', 'photos', 'cover', 'photo_count']

    def get_cover(self, obj):
        first = obj.photos.first()
        return first.image.url if first else None


class DealSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True, default='')
    listing_code = serializers.CharField(source='listing.listing_id', read_only=True, default='')
    listing_address = serializers.CharField(source='listing.address', read_only=True, default='')
    agent_net = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)

    class Meta:
        model = Deal
        fields = [
            'id', 'client', 'client_name', 'listing', 'listing_title', 'listing_code', 'listing_address',
            'stage', 'amount', 'currency', 'commission', 'platform_cut', 'agent_net', 'contract_signed',
            'note', 'created_at', 'closed_at',
        ]
        read_only_fields = ['id', 'client_name', 'listing_title', 'listing_code', 'listing_address', 'agent_net']


class ShowingSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_address = serializers.CharField(source='listing.address', read_only=True)
    listing_code = serializers.CharField(source='listing.listing_id', read_only=True)

    class Meta:
        model = Showing
        fields = [
            'id', 'client', 'client_name', 'listing', 'listing_title', 'listing_address',
            'listing_code', 'scheduled_at', 'status', 'note',
        ]
        read_only_fields = ['id', 'client_name', 'listing_title', 'listing_address', 'listing_code']


class ActivitySerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True, default='')

    class Meta:
        model = Activity
        fields = ['id', 'kind', 'text', 'client', 'client_name', 'created_at']
        read_only_fields = ['id', 'client_name']


class LeadCreateSerializer(serializers.Serializer):
    """Asosiy ilovadan/telegram'dan keladigan xom lead (agent tanlanmagan holda)."""

    name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=32)
    request = serializers.CharField(max_length=150)
    district = serializers.CharField(max_length=64, required=False, allow_blank=True)
    deal_type = serializers.CharField(max_length=16, required=False, allow_blank=True)
    budget_label = serializers.CharField(max_length=64, required=False, allow_blank=True)
    source = serializers.CharField(max_length=16, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
