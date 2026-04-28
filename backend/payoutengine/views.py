from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from payoutengine.models import Merchant, Payout, BankAccount, LedgerEntry
from payoutengine.serializers import (
    PayoutRequestSerializer,
    validate_idempotency_key,
)
from payoutengine.services.payout import (
    create_payout,
    InsufficientFundsError,
    IdempotencyConflictError,
    PayoutError,
)
from payoutengine.services.ledger import get_merchant_balance, get_held_balance
from .tasks import process_payout


class PingView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class MerchantListView(APIView):
    """
    GET /api/merchants
    Returns a list of all merchants.
    """

    def get(self, request):
        merchants = Merchant.objects.all().order_by("name")
        data = [
            {
                "merchantId": str(m.id),
                "merchantName": m.name,
            }
            for m in merchants
        ]
        return Response({"merchants": data})


class MerchantDetailView(APIView):
    """
    GET /api/merchant/<merchant_id>
    Returns merchant name, balance, and payout history.
    """

    def get(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except (Merchant.DoesNotExist, Exception):
            return Response(
                {"error": "Merchant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        balance = get_merchant_balance(merchant.id)

        held_balance = get_held_balance(merchant)

        payouts = (
            Payout.objects
            .filter(merchant=merchant)
            .select_related("bank_account")
            .order_by("-created_at")
        )

        payout_list = [
            {
                "payoutId": str(p.id),
                "requestedAt": p.created_at.isoformat(),
                "bankAccount": p.bank_account.account_number,
                "amount": p.amount,
                "status": p.status,
            }
            for p in payouts
        ]

        ledger_entries = (
            LedgerEntry.objects
            .filter(merchant=merchant)
            .order_by("-created_at")[:10]
        )

        ledger_list = [
            {
                "entryId": str(l.id),
                "type": l.entry_type,
                "amount": l.amount,
                "reference": l.reference,
                "createdAt": l.created_at.isoformat(),
                "payoutId": str(l.payout.id) if l.payout else None,
            }
            for l in ledger_entries
        ]

        return Response({
            "merchant": {
                "merchantName": merchant.name,
                "heldBalance": held_balance,
                "availableBalance": balance,
                "payouts": payout_list,
                "ledger": ledger_list,
            }
        })


class MerchantBankAccountsView(APIView):
    """
    GET /api/merchant/<merchant_id>/bank-accounts
    Returns the bank accounts belonging to a merchant.
    """

    def get(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except (Merchant.DoesNotExist, Exception):
            return Response(
                {"error": "Merchant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        accounts = BankAccount.objects.filter(
            merchant=merchant).order_by("account_number")
        data = [
            {
                "bankAccountId": str(a.id),
                "bankAccount": a.account_number,
            }
            for a in accounts
        ]
        return Response({"bankAccounts": data})


def _resolve_merchant(request) -> Merchant:
    """
    Resolve merchant from auth context.
    Uses X-Merchant-ID header for this challenge.
    In production this would come from token-based auth.
    """
    merchant_id = request.headers.get("X-Merchant-ID")
    if not merchant_id:
        return None
    try:
        return Merchant.objects.get(id=merchant_id)
    except (Merchant.DoesNotExist, Exception):
        return None


class PayoutCreateView(APIView):
    """
    POST /api/v1/payouts
    Creates a new payout request with idempotency support.
    """

    def post(self, request):
        # ── Authenticate / resolve merchant ──
        merchant = _resolve_merchant(request)
        if merchant is None:
            return Response(
                {"error": "Missing or invalid X-Merchant-ID header."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ── Validate Idempotency-Key header ──
        raw_key = request.headers.get("Idempotency-Key")
        if not raw_key:
            return Response(
                {"error": "Idempotency-Key header is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            idempotency_key = validate_idempotency_key(raw_key)
        except Exception:
            return Response(
                {"error": "Idempotency-Key must be a valid UUID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Validate request body ──
        serializer = PayoutRequestSerializer(
            data=request.data,
            context={"merchant": merchant},
        )
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount_paise = serializer.validated_data["amount_paise"]
        bank_account_id = serializer.validated_data["bank_account_id"]

        # ── Execute payout creation ──
        try:
            response_data, is_new = create_payout(
                merchant=merchant,
                idempotency_key=idempotency_key,
                amount_paise=amount_paise,
                bank_account_id=bank_account_id,
            )
            if is_new:
                process_payout.delay(response_data["payout_id"])
        except InsufficientFundsError as e:
            return Response(
                {"error": e.message},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except IdempotencyConflictError as e:
            return Response(
                {"error": e.message},
                status=status.HTTP_409_CONFLICT,
            )
        except PayoutError as e:
            return Response(
                {"error": e.message},
                status=e.status_code,
            )

        # Determine HTTP status:
        # - New payout → 201
        # - Idempotency hit on a stored error → 422 (return stored response verbatim)
        # - Idempotency hit on a stored success → 200
        if is_new:
            http_status = status.HTTP_201_CREATED
        elif response_data.get("error"):
            http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        else:
            http_status = status.HTTP_200_OK

        return Response(response_data, status=http_status)
