from django.urls import path

from . import views

urlpatterns = [
    path('send-code', views.send_code_view, name='auth-send-code'),
    path('send-code/', views.send_code_view),
    path('verify', views.verify_code_view, name='auth-verify'),
    path('verify/', views.verify_code_view),
    path('login/', views.password_login_view, name='auth-login'),
    path('me', views.me_view, name='auth-me'),
    path('me/', views.me_view),
    path('me/avatar', views.avatar_view, name='auth-avatar'),
    path('me/avatar/', views.avatar_view),
    path('me/phone', views.phone_change_request_view, name='auth-phone-change'),
    path('me/phone/', views.phone_change_request_view),
    path('me/phone/confirm', views.phone_change_confirm_view, name='auth-phone-confirm'),
    path('me/phone/confirm/', views.phone_change_confirm_view),
    # Uyimiz Agent bo'lish uchun ariza (avval SMS-kod bilan kirish shart)
    path('agent-apply', views.agent_apply_view, name='auth-agent-apply'),
    path('agent-apply/', views.agent_apply_view),

    path('logout', views.logout_view, name='auth-logout'),
    path('logout/', views.logout_view),
]
