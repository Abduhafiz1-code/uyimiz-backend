from django.conf import settings
from django.db import models
from django.utils import timezone


class DealType(models.TextChoices):
    SOTIB_OLISH = 'Sotib olish', 'Sotib olish'
    IJARA = 'Ijara', 'Ijara'
    KUNLIK = 'Kunlik', 'Kunlik'


class LeadSource(models.TextChoices):
    MOBIL = 'Mobil ilova', 'Mobil ilova'
    WEB = 'Web', 'Web'
    TELEGRAM = 'Telegram', 'Telegram'


class ClientStatus(models.TextChoices):
    QONGIROQ = "Qo'ng'iroq kutmoqda", "Qo'ng'iroq kutmoqda"
    KORSATUV = "Ko'rsatuv belgilandi", "Ko'rsatuv belgilandi"
    FOTOGA = 'Fotoga chiqish', 'Fotoga chiqish'
    SHARTNOMADA = 'Shartnomada', 'Shartnomada'
    YOPILGAN = 'Yopilgan', 'Yopilgan'
    RAD = 'Rad etilgan', 'Rad etilgan'


CLOSED_CLIENT_STATUSES = [ClientStatus.YOPILGAN, ClientStatus.RAD]


class Client(models.Model):
    """Xaridor/ijarachi lead — hudud+reyting bo'yicha agentga avtomatik biriktiriladi (docx 5-band)."""

    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32, blank=True)
    request = models.CharField(max_length=150, help_text='Masalan: 3 xona, Chilonzor')
    deal_type = models.CharField(max_length=16, choices=DealType.choices, default=DealType.SOTIB_OLISH)
    district = models.CharField(max_length=64, blank=True)
    budget_label = models.CharField(max_length=64, blank=True)
    budget_min = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    status = models.CharField(max_length=32, choices=ClientStatus.choices, default=ClientStatus.QONGIROQ)
    source = models.CharField(max_length=16, choices=LeadSource.choices, default=LeadSource.WEB)
    note = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    last_contact_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def initials(self):
        parts = [p for p in self.name.split() if p]
        return ''.join(p[0].upper() for p in parts[:2]) or '?'


class PropertyStatus(models.TextChoices):
    FAOL = 'Faol', 'Faol'
    BAND = 'Band', 'Band'
    SOTILGAN = 'Sotilgan', 'Sotilgan'
    ARXIV = 'Arxiv', 'Arxiv'


class PropertyBadge(models.TextChoices):
    ODDIY = 'Oddiy', 'Oddiy'
    VIP = 'VIP', 'VIP'
    PREMIUM = 'Premium', 'Premium'


class Property(models.Model):
    """Agent portfeli — istasa bitta jamoat e'loniga (listings.Listing) bog'lanadi."""

    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='properties')
    public_listing = models.OneToOneField(
        'listings.Listing', on_delete=models.SET_NULL, null=True, blank=True, related_name='crm_property'
    )
    listing_id = models.CharField(max_length=16, unique=True, help_text="Platformadagi e'lon ID")
    title = models.CharField(max_length=150)
    district = models.CharField(max_length=64)
    address = models.CharField(max_length=200)
    deal_type = models.CharField(max_length=16, choices=DealType.choices, default=DealType.SOTIB_OLISH)
    price = models.DecimalField(max_digits=14, decimal_places=0)
    currency = models.CharField(max_length=8, default='USD')
    rooms = models.PositiveSmallIntegerField(default=1)
    area = models.DecimalField(max_digits=6, decimal_places=1)
    floor = models.PositiveSmallIntegerField(default=1)
    total_floors = models.PositiveSmallIntegerField(default=1)
    built_year = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=PropertyStatus.choices, default=PropertyStatus.FAOL)
    badge = models.CharField(max_length=16, choices=PropertyBadge.choices, default=PropertyBadge.ODDIY)
    is_verified = models.BooleanField(default=True)
    owner_name = models.CharField(max_length=150, blank=True)
    owner_phone = models.CharField(max_length=32, blank=True)
    photo_count = models.PositiveSmallIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'properties'

    def __str__(self):
        return f'{self.listing_id} — {self.title}'

    @property
    def price_label(self):
        if self.currency == 'UZS':
            return f'{self.price:,.0f}'.replace(',', ' ') + " so'm"
        return '$' + f'{self.price:,.0f}'.replace(',', ' ')

    def sync_photo_count(self):
        count = PropertyPhoto.objects.filter(listing=self).count()
        if count != self.photo_count:
            Property.objects.filter(pk=self.pk).update(photo_count=count)
            self.photo_count = count


def listing_photo_path(instance, filename):
    return f'crm-properties/{instance.listing.listing_id}/{filename}'


class PropertyPhoto(models.Model):
    listing = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=listing_photo_path)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['order', 'id']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.listing.sync_photo_count()

    def delete(self, *args, **kwargs):
        listing = self.listing
        super().delete(*args, **kwargs)
        listing.sync_photo_count()


class DealStage(models.TextChoices):
    KORSATUV = "Ko'rsatuv", "Ko'rsatuv"
    KELISHUV = 'Kelishuv', 'Kelishuv'
    SHARTNOMA = 'Shartnoma', 'Shartnoma'
    YOPILGAN = 'Yopilgan', 'Yopilgan'
    BEKOR = 'Bekor qilingan', 'Bekor qilingan'


OPEN_DEAL_STAGES = [DealStage.KORSATUV, DealStage.KELISHUV, DealStage.SHARTNOMA]


class Deal(models.Model):
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deals')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='deals')
    listing = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True, related_name='deals')
    stage = models.CharField(max_length=20, choices=DealStage.choices, default=DealStage.KORSATUV)
    amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    currency = models.CharField(max_length=8, default='USD')
    commission = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    platform_cut = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    contract_signed = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.client.name} — {self.stage}'

    @property
    def agent_net(self):
        return self.commission - self.platform_cut


class ShowingStatus(models.TextChoices):
    REJALASHTIRILGAN = 'Rejalashtirilgan', 'Rejalashtirilgan'
    BOLDI = "Bo'lib o'tdi", "Bo'lib o'tdi"
    BEKOR = 'Bekor qilingan', 'Bekor qilingan'


class Showing(models.Model):
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='showings')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='showings')
    listing = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='showings')
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=ShowingStatus.choices, default=ShowingStatus.REJALASHTIRILGAN)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f'{self.client.name} — {self.listing.listing_id}'


class ActivityKind(models.TextChoices):
    MIJOZ = 'mijoz', 'Yangi mijoz'
    QONGIROQ = "qo'ng'iroq", "Qo'ng'iroq"
    KORSATUV = "ko'rsatuv", "Ko'rsatuv"
    BITIM = 'bitim', 'Bitim'
    SHARTNOMA = 'shartnoma', 'Shartnoma'
    REYTING = 'reyting', 'Reyting'


class Activity(models.Model):
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    kind = models.CharField(max_length=16, choices=ActivityKind.choices)
    text = models.CharField(max_length=250)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'activities'

    def __str__(self):
        return self.text
