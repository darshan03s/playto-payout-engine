from django.urls import path
from .views import PingView, PayoutCreateView, MerchantListView

urlpatterns = [
    path('ping/', PingView.as_view()),
    path('merchants/', MerchantListView.as_view(), name='merchant-list'),
    path('v1/payouts/', PayoutCreateView.as_view(), name='payout-create'),
]
