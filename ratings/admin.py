from django.contrib import admin

from .models import Rating


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['rater', 'target_type', 'target_user', 'target_listing', 'score', 'created_at']
    list_filter = ['target_type', 'score']
