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
    path('logout', views.logout_view, name='auth-logout'),
    path('logout/', views.logout_view),
]
