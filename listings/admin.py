from django.contrib import admin

from .models import ChatMessage, ChatThread, Contract, Favorite, Listing, ListingPhoto


class ListingPhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 0


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['id', 'district', 'address', 'deal', 'price', 'status', 'badge', 'verified', 'owner', 'agent']
    list_filter = ['status', 'badge', 'deal', 'ptype', 'verified', 'district']
    search_fields = ['address', 'district', 'owner__phone', 'owner__name']
    inlines = [ListingPhotoInline]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'listing', 'created_at']


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ['listing', 'buyer', 'created_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['thread', 'sender', 'text', 'created_at']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['id', 'listing', 'seller', 'buyer', 'agent', 'status', 'price', 'created_at']
    list_filter = ['status', 'deal']
