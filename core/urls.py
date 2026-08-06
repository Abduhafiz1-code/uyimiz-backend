from django.urls import path

from . import views

urlpatterns = [
    path('districts', views.districts_view, name='districts'),
    path('districts/', views.districts_view),
]
