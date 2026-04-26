import uuid
from datetime import timedelta
from typing import Tuple

from django.db import transaction, IntegrityError
from django.utils import timezone

from payoutengine.models import (
    Merchant,
    Payout,
    LedgerEntry,
    IdempotencyKey,
)
from payoutengine.services.ledger import get_merchant_balance


class PayoutError(Exception):
    """Base exception for payout service errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InsufficientFundsError(PayoutError):
    def __init__(self):
        super().__init__("Insufficient funds.", status_code=422)


class IdempotencyConflictError(PayoutError):
    """Request with this idempotency key is still in-flight."""
    def __init__(self):
        super().__init__(
            "A request with this idempotency key is already in progress.",
            status_code=409,
        )


class IdempotencyHitResult:
    """Returned when an idempotency key has already been processed."""
    def __init__(self, response_data: dict):
        self.response_data = response_data


def _build_response_data(payout: Payout) -> dict:
    return {
        "payout_id": str(payout.id),
        "status": payout.status,
        "amount_paise": payout.amount,
    }


def create_payout(
    merchant: Merchant,
    idempotency_key: uuid.UUID,
    amount_paise: int,
    bank_account_id: uuid.UUID,
) -> Tuple[dict, bool]:
    """
    Create a payout within a single atomic database transaction.

    Returns:
        Tuple of (response_data dict, is_new: bool).
        is_new=False means this was an idempotency hit.

    Raises:
        InsufficientFundsError: if merchant balance < amount_paise
        IdempotencyConflictError: if a request with the same key is still in-flight
    """
    with transaction.atomic():
        # ── Step 1: Idempotency handling (race-safe inside transaction) ──
        idempotency_result = _handle_idempotency(merchant, idempotency_key)

        if isinstance(idempotency_result, IdempotencyHitResult):
            # Exact duplicate — return stored response verbatim.
            # This guarantees identical responses for the same key,
            # whether the original was a success or a failure.
            return idempotency_result.response_data, False

        # idempotency_result is the newly created IdempotencyKey row
        idem_record: IdempotencyKey = idempotency_result

        # ── Step 2: Lock merchant row (SELECT FOR UPDATE) ──
        # This serialises concurrent payouts for the same merchant.
        locked_merchant = (
            Merchant.objects
            .select_for_update()
            .get(id=merchant.id)
        )

        # ── Step 3: Compute available balance at DB level ──
        available_balance = get_merchant_balance(locked_merchant.id)

        # ── Step 4: Validate sufficient funds ──
        if available_balance < amount_paise:
            # Store failure in idempotency record so the key doesn't get
            # stuck with null response_data for 24h.
            error_response = {
                "error": "Insufficient funds.",
                "status": "rejected",
            }
            idem_record.response_data = error_response
            idem_record.save(update_fields=["response_data", "updated_at"])
            raise InsufficientFundsError()

        # ── Step 5: Create payout record ──
        payout = Payout.objects.create(
            merchant=locked_merchant,
            bank_account_id=bank_account_id,
            amount=amount_paise,
            status=Payout.Status.PENDING,
        )

        # ── Step 6: Create ledger entry (DEBIT — hold funds) ──
        LedgerEntry.objects.create(
            merchant=locked_merchant,
            amount=amount_paise,
            entry_type=LedgerEntry.EntryType.DEBIT,
            payout=payout,
            reference=f"payout_hold:{payout.id}",
        )

        # ── Step 7: Store idempotency response ──
        response_data = _build_response_data(payout)
        idem_record.payout = payout
        idem_record.response_data = response_data
        idem_record.save(update_fields=["payout", "response_data", "updated_at"])

    # ── Step 8: Transaction committed — return response ──
    return response_data, True


def _handle_idempotency(
    merchant: Merchant,
    idempotency_key: uuid.UUID,
) -> "IdempotencyKey | IdempotencyHitResult":
    """
    Attempt to insert a new idempotency record.
    - If insert succeeds → return the new IdempotencyKey (first request).
    - If insert fails (unique constraint) → lock existing row:
        - If response_data exists → return IdempotencyHitResult (duplicate).
        - If response_data is null → raise IdempotencyConflictError (in-flight).
    """
    expires_at = timezone.now() + timedelta(hours=24)

    try:
        # Use a savepoint so the IntegrityError doesn't break the outer txn
        with transaction.atomic():
            idem_record = IdempotencyKey.objects.create(
                merchant=merchant,
                key=idempotency_key,
                expires_at=expires_at,
            )
        return idem_record

    except IntegrityError:
        # Unique constraint violation — key already exists
        existing = (
            IdempotencyKey.objects
            .select_for_update()
            .get(merchant=merchant, key=idempotency_key)
        )

        # ── Expiry check: expired keys are treated as fresh requests ──
        if existing.expires_at <= timezone.now():
            existing.delete()
            # Re-create with a fresh expiry
            idem_record = IdempotencyKey.objects.create(
                merchant=merchant,
                key=idempotency_key,
                expires_at=expires_at,
            )
            return idem_record

        if existing.response_data is not None:
            # Already processed — idempotency hit
            return IdempotencyHitResult(response_data=existing.response_data)

        # Still in-flight (response_data is null)
        raise IdempotencyConflictError()
