"""Asosiy ilova: e'lonlar, sevimlilar, chat, onlayn shartnoma.

docx 2.2-band: "E'lon joylash", "Qidiruv tizimi", "Chat va aloqa",
"Onlayn shartnoma", "Reyting tizimi" — barchasi shu modellarga tayanadi.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class DealKind(models.TextChoices):
    SALE = 'sale', 'Sotish'
    RENT = 'rent', 'Ijara'
    DAILY = 'daily', 'Kunlik ijara'


class PropertyType(models.TextChoices):
    APARTMENT = 'apartment', 'Kvartira'
    NEWBUILD = 'newbuild', 'Yangi qurilish'
    HOUSE = 'house', 'Hovli uy'
    COMMERCIAL = 'commercial', 'Tijorat'


class RepairState(models.TextChoices):
    EURO = 'euro', 'Yevro remont'
    DESIGNER = 'designer', 'Dizaynerlik'
    GOOD = 'good', "O'rtacha"
    AVERAGE = 'average', 'Qoniqarli'
    NONE = 'none', "Ta'mirsiz"


class DocsState(models.TextChoices):
    READY = 'ready', 'Hujjatlar tayyor'
    PROCESS = 'process', 'Rasmiylashtirilmoqda'


class ListingStatus(models.TextChoices):
    """Moderatsiya + hayot bosqichi — admin panel shu maydonni boshqaradi."""

    PENDING = 'pending', 'Kutilmoqda'
    ACTIVE = 'active', 'Faol'
    REJECTED = 'rejected', 'Rad etilgan'
    DEALT = 'dealt', 'Bitim tuzilgan'
    ARCHIVED = 'archived', 'Arxiv'


class ListingBadge(models.TextChoices):
    """2-bosqich: "Top e'lon" va "Premium joylashuv" (moliyaviy model, 4-band)."""

    ODDIY = 'oddiy', 'Oddiy'
    PREMIUM = 'premium', 'Premium'
    VIP = 'vip', 'VIP'


class Listing(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    #: Agar bu e'lon "Uyimiz Agent" tomonidan joylashtirilgan/boshqarilayotgan bo'lsa.
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='agent_listings', limit_choices_to={'role': 'agent'},
    )

    deal = models.CharField(max_length=8, choices=DealKind.choices, default=DealKind.SALE)
    district = models.CharField(max_length=64, db_index=True)
    address = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default='usd')

    rooms = models.PositiveSmallIntegerField(default=1)
    area = models.DecimalField(max_digits=7, decimal_places=1, default=Decimal('0'))
    floor = models.PositiveSmallIntegerField(default=1)
    floors = models.PositiveSmallIntegerField(default=1)
    year = models.PositiveSmallIntegerField(default=2020)
    ptype = models.CharField(max_length=16, choices=PropertyType.choices, default=PropertyType.APARTMENT)
    repair = models.CharField(max_length=16, choices=RepairState.choices, default=RepairState.GOOD)
    docs = models.CharField(max_length=16, choices=DocsState.choices, default=DocsState.READY)
    features = models.JSONField(default=list, blank=True)

    verified = models.BooleanField(default=False, help_text='Real foto/joylashuv tasdiqlangan (AI + admin)')
    contract_ready = models.BooleanField(default=True)
    status = models.CharField(max_length=12, choices=ListingStatus.choices, default=ListingStatus.PENDING)
    badge = models.CharField(max_length=8, choices=ListingBadge.choices, default=ListingBadge.ODDIY)
    promoted_until = models.DateTimeField(null=True, blank=True)

    rating_avg = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('0.0'))
    rating_count = models.PositiveIntegerField(default=0)

    views = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.id} — {self.district}, {self.address}'

    @property
    def by_agent(self):
        return self.agent_id is not None

    @property
    def promoted(self):
        return bool(self.promoted_until and self.promoted_until >= timezone.now())

    @property
    def is_new(self):
        return (timezone.now() - self.created_at).total_seconds() < 72 * 3600


def listing_photo_path(instance, filename):
    return f'listings/{instance.listing_id}/{filename}'


class ListingPhoto(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=listing_photo_path)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.listing_id} — foto {self.order}'


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['user', 'listing']


class ChatThread(models.Model):
    """Bitta e'lon bo'yicha bitta xaridor ↔ egasi suhbati (2.2-band: "Chat va aloqa")."""

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='chat_threads')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_threads')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['listing', 'buyer']

    def __str__(self):
        return f'{self.listing_id} ↔ {self.buyer_id}'


class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    text = models.CharField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']


class ContractStatus(models.TextChoices):
    DRAFT = 'draft', 'Loyihada'
    SIGNED = 'signed', 'Imzolangan'
    CANCELLED = 'cancelled', 'Bekor qilingan'


def contract_pdf_path(instance, filename):
    return f'contracts/{instance.id}/{filename}'


class Contract(models.Model):
    """2.2-band: "Onlayn shartnoma: Platforma avtomatik ravishda shartnoma yaratadi (PDF/E-imzo)"."""

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='contracts')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contracts_as_seller')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contracts_as_buyer')
    #: Agar bitim "Uyimiz Agent" ishtirokida bo'lsa — CRM.Deal shu yerdan yaratiladi.
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    deal = models.CharField(max_length=8, choices=DealKind.choices)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default='usd')
    #: 3-bosqich, 4-band: onlayn shartnoma xizmat haqi (masalan 50 000 so'm).
    service_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    seller_signed = models.BooleanField(default=True)
    buyer_signed = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=ContractStatus.choices, default=ContractStatus.DRAFT)
    pdf = models.FileField(upload_to=contract_pdf_path, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    signed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'C-{self.id} — {self.listing_id}'
