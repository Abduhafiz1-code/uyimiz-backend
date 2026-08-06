"""Butun platformani boshqaruvchi admin panel: moderatsiya, tariflar,
komissiya/bosqich sozlamalari, audit jurnali (docx: admin-backend vazifasi).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class ModerationItem(models.Model):
    """AI/qo'lda tekshiruv kutayotgan e'lonlar navbati (docx 3-bosqich: "AI asosida
    feyk e'lonlar filtrlash tizimi")."""

    listing = models.OneToOneField('listings.Listing', on_delete=models.CASCADE, related_name='moderation')
    reason = models.CharField(max_length=200, blank=True)
    #: 0-100 — AI shubha balli. Admin panel sozlamasidagi aiThreshold shu bilan solishtiriladi.
    score = models.PositiveSmallIntegerField(default=50)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.listing_id} — {self.reason or 'tekshiruv kutilmoqda'}"


class Tariff(models.Model):
    """Moliyaviy model (docx 4-band): Premium/VIP/shartnoma/agent obunasi narxlari."""

    name = models.CharField(max_length=150)
    price_label = models.CharField(max_length=64, help_text="Masalan '70 000 so\\'m' yoki 'Bepul'")
    period = models.CharField(max_length=32, blank=True, help_text="oy / hafta / shartnoma / yil / —")
    description = models.CharField(max_length=250, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class PlatformSettings(models.Model):
    """Singleton — docx 4-band (moliyaviy model) va 3-band (bosqichlar) shu yerda saqlanadi."""

    ai_threshold = models.PositiveSmallIntegerField(default=80, help_text='AI filtr chegara balli')
    deal_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.5, help_text="Platforma komissiyasi (muvaffaqiyatli bitimdan), %"
    )
    contract_price = models.PositiveIntegerField(default=50000, help_text="Onlayn shartnoma xizmat haqi, so'm")
    vip_price = models.PositiveIntegerField(default=200000, help_text="VIP joylashuv narxi, so'm/hafta")
    premium_post_price = models.PositiveIntegerField(default=70000, help_text="Premium e'lon narxi, so'm/oy")
    agent_commission_percent = models.DecimalField(
        max_digits=4, decimal_places=2, default=2, help_text='Uyimiz Agent fiks komissiyasi, %'
    )
    platform_share_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=12, help_text="Platformaning agentdan ulushi, %"
    )
    agent_subscription_price = models.PositiveIntegerField(default=400000, help_text='Agent oylik obunasi')
    #: 1 = Maklersiz pilot, 2 = Tizimlashtirish/monetizatsiya, 3 = Maklerlar bilan integratsiya (docx 3-band).
    stage = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = 'Platforma sozlamalari'
        verbose_name_plural = 'Platforma sozlamalari'

    def __str__(self):
        return 'Platforma sozlamalari'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AuditLog(models.Model):
    """Har bir admin harakati shu yerda qayd etiladi (shaffoflik, docx missiyasi)."""

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    admin_label = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=200)
    object_label = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} — {self.object_label}'


def log_action(admin_user, action, object_label=''):
    AuditLog.objects.create(
        admin=admin_user if getattr(admin_user, 'is_authenticated', False) else None,
        admin_label=getattr(admin_user, 'name', 'Superadmin') if admin_user else 'Superadmin',
        action=action,
        object_label=str(object_label),
    )
