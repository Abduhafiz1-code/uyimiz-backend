from django.contrib import admin

from .models import AuditLog, ModerationItem, PlatformSettings, Tariff


@admin.register(ModerationItem)
class ModerationItemAdmin(admin.ModelAdmin):
    list_display = ['listing', 'reason', 'score', 'created_at']


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_label', 'period', 'order']


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ['stage', 'deal_commission_percent', 'contract_price', 'vip_price']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'object_label', 'admin_label', 'created_at']
    list_filter = ['action']
