"""Ochiq (autentifikatsiyasiz) accounts endpointlari.

Bular `/api/auth/...` ostida emas, to'g'ridan-to'g'ri `/api/...` ostida
turadi, chunki bu ma'lumot autentifikatsiyaga aloqador emas — bu oddiy
katalog: sayt va mobil ilovaning "Agentlar" bo'limi.
"""
from django.urls import path

from . import views

urlpatterns = [
    path('agents', views.agents_list_view, name='agents-list'),
    path('agents/', views.agents_list_view),
    path('agents/<int:pk>', views.agent_detail_view, name='agent-detail'),
    path('agents/<int:pk>/', views.agent_detail_view),
]
