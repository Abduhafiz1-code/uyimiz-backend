from django.contrib import admin

from .models import Activity, Client, Deal, Property, Showing


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'agent', 'request', 'budget_label', 'status', 'source', 'created_at']
    list_filter = ['status', 'source', 'deal_type']
    search_fields = ['name', 'phone', 'request']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['listing_id', 'title', 'district', 'price', 'status', 'badge', 'agent']
    list_filter = ['status', 'badge', 'deal_type', 'district']
    search_fields = ['listing_id', 'title', 'address']


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ['client', 'listing', 'stage', 'amount', 'commission', 'agent', 'closed_at']
    list_filter = ['stage']


@admin.register(Showing)
class ShowingAdmin(admin.ModelAdmin):
    list_display = ['client', 'listing', 'scheduled_at', 'status', 'agent']
    list_filter = ['status']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['text', 'kind', 'agent', 'created_at']
    list_filter = ['kind']
