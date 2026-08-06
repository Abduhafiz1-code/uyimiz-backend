from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import PhoneOTP, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ['-date_joined']
    list_display = ['phone', 'name', 'role', 'is_active', 'verified', 'rating', 'tier', 'date_joined']
    list_filter = ['role', 'is_active', 'verified', 'certification']
    search_fields = ['phone', 'name', 'email']
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Shaxsiy ma\'lumot', {'fields': ('name', 'email', 'district', 'user_kind')}),
        ('Rol', {'fields': ('role', 'admin_title', 'verified')}),
        ('Agent', {
            'fields': (
                'rating', 'rating_count', 'tier', 'certification', 'platform_share',
                'commission_rate', 'avg_response_minutes', 'historical_deals', 'total_deals',
            )
        }),
        ('Ruxsatlar', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Sanalar', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('phone', 'name', 'role', 'password1', 'password2')}),
    )
    readonly_fields = ['last_login', 'date_joined']


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ['phone', 'code', 'created_at', 'expires_at', 'consumed']
    search_fields = ['phone']
