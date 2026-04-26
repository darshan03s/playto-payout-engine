from django.urls import path
from .views import PingView, PayoutCreateView, MerchantListView, MerchantDetailView, MerchantBankAccountsView

urlpatterns = [
    path('ping/', PingView.as_view()),
    path('merchants/', MerchantListView.as_view(), name='merchant-list'),
    path('merchant/<uuid:merchant_id>/', MerchantDetailView.as_view(), name='merchant-detail'),
    path('merchant/<uuid:merchant_id>/bank-accounts/', MerchantBankAccountsView.as_view(), name='merchant-bank-accounts'),
    path('v1/payouts/', PayoutCreateView.as_view(), name='payout-create'),
]
