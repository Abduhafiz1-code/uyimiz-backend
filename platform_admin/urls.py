from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('users', views.AdminUserViewSet, basename='admin-user')
router.register('agents', views.AdminAgentViewSet, basename='admin-agent')
router.register('posts', views.AdminListingViewSet, basename='admin-post')
router.register('moderation', views.ModerationViewSet, basename='admin-moderation')
router.register('tariffs', views.TariffViewSet, basename='admin-tariff')
router.register('admins', views.AdminAccountViewSet, basename='admin-account')

urlpatterns = [
    path('dashboard', views.dashboard_view, name='admin-dashboard'),
    path('dashboard/', views.dashboard_view),
    path('audit', views.audit_view, name='admin-audit'),
    path('audit/', views.audit_view),
    path('settings', views.settings_view, name='admin-settings'),
    path('settings/', views.settings_view),
    path('', include(router.urls)),
]
