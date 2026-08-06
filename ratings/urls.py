from django.urls import path

from . import views

urlpatterns = [
    path('contracts/<int:pk>/rate', views.rate_contract_view, name='rate-contract'),
    path('contracts/<int:pk>/rate/', views.rate_contract_view),
    path('users/<int:pk>/ratings', views.user_ratings_view, name='user-ratings'),
    path('users/<int:pk>/ratings/', views.user_ratings_view),
]
