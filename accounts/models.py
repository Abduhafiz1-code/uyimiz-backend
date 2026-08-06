"""Uyimiz.uz — yagona foydalanuvchi modeli.

Loyihaning markaziy g'oyasi shu yerda: oddiy foydalanuvchi (uy egasi /
xaridor / ijarachi), Uyimiz Agent (makler) va platforma admin/superadmini —
UCHALASI HAM shu bitta ``User`` jadvalida, bitta autentifikatsiya tizimi
(telefon + token) orqali ishlaydi. Ularni faqat ``role`` maydoni ajratib
turadi, shuning uchun butun backend chindan ham bitta-butun tizim bo'ladi:
CRM ham, admin panel ham, asosiy ilova ham bir xil foydalanuvchi va token
jadvaliga murojaat qiladi.
"""
from decimal import Decimal

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    USER = 'user', 'Foydalanuvchi'
    AGENT = 'agent', 'Uyimiz Agent'
    ADMIN = 'admin', 'Admin'
    SUPERADMIN = 'superadmin', 'Superadmin'


class UserKind(models.TextChoices):
    """Oddiy foydalanuvchi turi — admin paneldagi 'Uy egasi/Xaridor/Ijarachi'."""

    OWNER = 'owner', 'Uy egasi'
    BUYER = 'buyer', 'Xaridor'
    TENANT = 'tenant', 'Ijarachi'


class AgentTier(models.TextChoices):
    YANGI = 'Yangi', 'Yangi agent'
    FAOL = 'Faol', 'Faol makler'
    TAJRIBALI = 'Tajribali', 'Tajribali makler'
    TOP = 'Top', 'Top Makler'


TIER_THRESHOLDS = {
    AgentTier.YANGI: 0,
    AgentTier.FAOL: 5,
    AgentTier.TAJRIBALI: 15,
    AgentTier.TOP: 40,
}
TIER_ORDER = [AgentTier.YANGI, AgentTier.FAOL, AgentTier.TAJRIBALI, AgentTier.TOP]


class CertificationStatus(models.TextChoices):
    KUTILMOQDA = 'Kutilmoqda', 'Kutilmoqda'
    TASDIQLANGAN = 'Tasdiqlangan', 'Tasdiqlangan'
    RAD = 'Rad etilgan', 'Rad etilgan'
    BEKOR = 'Bekor qilindi', 'Bekor qilindi'


class AdminTitle(models.TextChoices):
    SUPERADMIN = 'Superadmin', 'Superadmin'
    ADMIN = 'Admin', 'Admin'
    MODERATOR = 'Moderator', 'Moderator'


def normalize_phone(raw: str) -> str:
    """``+998901234567`` / ``901234567`` / ``90 123 45 67`` -> ``+998901234567``."""
    digits = ''.join(ch for ch in str(raw or '') if ch.isdigit())
    digits = digits[-9:] if len(digits) >= 9 else digits
    return '+998' + digits if digits else ''


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, phone, password, **extra):
        phone = normalize_phone(phone)
        if not phone or len(phone) < 12:
            raise ValueError("Telefon raqami noto'g'ri")
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra):
        extra.setdefault('role', Role.USER)
        return self._create(phone, password, **extra)

    def create_agent(self, phone, password=None, **extra):
        extra['role'] = Role.AGENT
        extra.setdefault('certification', CertificationStatus.KUTILMOQDA)
        return self._create(phone, password, **extra)

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault('role', Role.SUPERADMIN)
        extra.setdefault('admin_title', AdminTitle.SUPERADMIN)
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('verified', True)
        return self._create(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Yagona akkaunt: oddiy foydalanuvchi, Uyimiz Agent yoki admin."""

    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150, default='Foydalanuvchi', blank=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.USER, db_index=True)
    user_kind = models.CharField(max_length=16, choices=UserKind.choices, default=UserKind.BUYER)
    verified = models.BooleanField(default=False, help_text='myID yoki SMS orqali tasdiqlangan')
    avatar_initials = models.CharField(max_length=4, blank=True)
    district = models.CharField(max_length=64, blank=True, help_text='Agent uchun biriktirilgan hudud')

    # ---- Uyimiz Agent (makler) maydonlari -------------------------------
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('0.0'))
    rating_count = models.PositiveIntegerField(default=0)
    tier = models.CharField(max_length=16, choices=AgentTier.choices, default=AgentTier.YANGI)
    certification = models.CharField(
        max_length=20, choices=CertificationStatus.choices, default=CertificationStatus.KUTILMOQDA
    )
    platform_share = models.PositiveSmallIntegerField(default=12, help_text="Platformaning agentdan ulushi, %")
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.50'))
    avg_response_minutes = models.PositiveIntegerField(default=0)
    historical_deals = models.PositiveIntegerField(default=0)
    total_deals = models.PositiveIntegerField(default=0)

    # ---- Admin panel maydonlari ------------------------------------------
    admin_title = models.CharField(max_length=16, choices=AdminTitle.choices, blank=True)

    is_active = models.BooleanField(default=True)  # False = "Bloklangan"
    is_staff = models.BooleanField(default=False)  # Django /admin/ ga kirish huquqi
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.name} ({self.phone})'

    def save(self, *args, **kwargs):
        if self.role in (Role.ADMIN, Role.SUPERADMIN):
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def initials(self):
        if self.avatar_initials:
            return self.avatar_initials
        parts = [p for p in self.name.split() if p]
        return ''.join(p[0].upper() for p in parts[:2]) or self.phone[-2:]

    @property
    def status_label(self):
        return 'Faol' if self.is_active else 'Bloklangan'

    @property
    def next_tier(self):
        try:
            index = TIER_ORDER.index(AgentTier(self.tier))
        except ValueError:
            index = 0
        if index + 1 >= len(TIER_ORDER):
            return None
        return TIER_ORDER[index + 1]

    def tier_progress(self):
        nxt = self.next_tier
        if nxt is None:
            return 100, 0, None
        floor = TIER_THRESHOLDS[AgentTier(self.tier)]
        ceiling = TIER_THRESHOLDS[nxt]
        span = max(ceiling - floor, 1)
        done = max(self.total_deals - floor, 0)
        percent = min(round(done / span * 100), 100)
        return percent, max(ceiling - self.total_deals, 0), nxt.label

    def recalc_tier(self):
        total = self.historical_deals + self.total_deals_from_crm()
        tier = TIER_ORDER[0]
        for candidate in TIER_ORDER:
            if total >= TIER_THRESHOLDS[candidate]:
                tier = candidate
        self.total_deals = total
        self.tier = tier
        self.save(update_fields=['total_deals', 'tier'])

    def total_deals_from_crm(self):
        from crm.models import Deal, DealStage
        return self.deals.filter(stage=DealStage.YOPILGAN).count()

    def apply_rating(self, score):
        """Yangi bahoni o'rtacha reytingga qo'shadi (agentlar va reytingli userlar uchun)."""
        total = self.rating * self.rating_count + Decimal(score)
        self.rating_count += 1
        self.rating = round(total / self.rating_count, 1)
        self.save(update_fields=['rating', 'rating_count'])


class PhoneOTP(models.Model):
    """SMS-kod orqali tasdiqlash (2.2-band: 'Verifikatsiya: myID yoki SMS')."""

    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)

    def is_valid(self, code):
        return not self.consumed and self.code == code and timezone.now() <= self.expires_at

    def __str__(self):
        return f'{self.phone} — {self.code}'
