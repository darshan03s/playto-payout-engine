from django.urls import path
from .views import PingView, PayoutCreateView, MerchantListView, MerchantDetailView

urlpatterns = [
    path('ping/', PingView.as_view()),
    path('merchants/', MerchantListView.as_view(), name='merchant-list'),
    path('merchant/<uuid:merchant_id>/', MerchantDetailView.as_view(), name='merchant-detail'),
    path('v1/payouts/', PayoutCreateView.as_view(), name='payout-create'),
]
