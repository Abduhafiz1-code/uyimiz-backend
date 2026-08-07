from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('listings', views.ListingViewSet, basename='listing')

urlpatterns = [
    path('favorites', views.favorites_view, name='favorites'),
    path('favorites/', views.favorites_view),
    path('favorites/<int:pk>', views.favorite_toggle_view, name='favorite-toggle'),
    path('favorites/<int:pk>/', views.favorite_toggle_view),

    path('listings/<int:pk>/chat', views.listing_chat_view, name='listing-chat'),
    path('listings/<int:pk>/chat/', views.listing_chat_view),
    path('me/chats', views.my_chats_view, name='my-chats'),
    path('me/chats/', views.my_chats_view),

    path('listings/<int:pk>/contract', views.create_contract_view, name='create-contract'),
    path('listings/<int:pk>/contract/', views.create_contract_view),
    path('contracts/<int:pk>/approve', views.approve_contract_view, name='approve-contract'),
    path('contracts/<int:pk>/approve/', views.approve_contract_view),
    path('contracts/<int:pk>/cancel', views.cancel_contract_view, name='cancel-contract'),
    path('contracts/<int:pk>/cancel/', views.cancel_contract_view),
    path('contracts/<int:pk>/sign-request', views.sign_request_view, name='sign-request'),
    path('contracts/<int:pk>/sign-request/', views.sign_request_view),
    path('contracts/<int:pk>/sign', views.sign_contract_view, name='sign-contract'),
    path('contracts/<int:pk>/sign/', views.sign_contract_view),
    path('contracts/<int:pk>', views.contract_detail_view, name='contract-detail'),
    path('contracts/<int:pk>/', views.contract_detail_view),
    path('me/contracts', views.my_contracts_view, name='my-contracts'),
    path('me/contracts/', views.my_contracts_view),

    path('me/listings', views.ListingViewSet.as_view({'get': 'mine'}), name='my-listings'),
    path('me/listings/', views.ListingViewSet.as_view({'get': 'mine'})),

    path('', include(router.urls)),
]
