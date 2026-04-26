from django.urls import path
from .views import PingView, PayoutCreateView

urlpatterns = [
    path('ping/', PingView.as_view()),
    path('v1/payouts/', PayoutCreateView.as_view(), name='payout-create'),
]
