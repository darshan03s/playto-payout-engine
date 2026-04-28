from celery import shared_task
from django.db import transaction
from payoutengine.models import Payout
from django.utils import timezone
import random
from payoutengine.models import LedgerEntry
import time
from django.conf import settings


def assert_valid_transition(from_state: str, to_state: str):
    allowed = {
        Payout.Status.PENDING: [Payout.Status.PROCESSING],
        Payout.Status.PROCESSING: [Payout.Status.COMPLETED, Payout.Status.FAILED],
        Payout.Status.COMPLETED: [],
        Payout.Status.FAILED: [],
    }

    if to_state not in allowed.get(from_state, []):
        raise ValueError(f"Invalid transition {from_state} → {to_state}")


@shared_task
def debug_task(x, y):
    return x + y


PROCESSING_DELAY_SECONDS = 0 if getattr(settings, "IS_TEST", False) else 30


@shared_task
def process_payout(payout_id):
    with transaction.atomic():
        payout = (
            Payout.objects
            .select_for_update()
            .get(id=payout_id)
        )

        if payout.status == Payout.Status.PROCESSING:
            if payout.last_attempt_at and (timezone.now() - payout.last_attempt_at).total_seconds() < 30:
                return

        elif payout.status != Payout.Status.PENDING:
            return

        assert_valid_transition(payout.status, Payout.Status.PROCESSING)

        payout.status = Payout.Status.PROCESSING
        payout.last_attempt_at = timezone.now()
        payout.save(update_fields=["status", "last_attempt_at", "updated_at"])

    print(
        f"Processing payout {payout_id}... sleeping for {PROCESSING_DELAY_SECONDS}s")
    time.sleep(PROCESSING_DELAY_SECONDS)

    outcome = random.random()

    if outcome < 0.7:
        result = "success"
    elif outcome < 0.9:
        result = "failure"
    else:
        result = "retry"

    if result == 'success':
        with transaction.atomic():
            payout = (
                Payout.objects
                .select_for_update()
                .get(id=payout_id)
            )

            if payout.status != Payout.Status.PROCESSING:
                return

            assert_valid_transition(payout.status, Payout.Status.COMPLETED)

            payout.status = Payout.Status.COMPLETED
            payout.save(update_fields=["status", "updated_at"])

    elif result == "failure":
        with transaction.atomic():
            payout = (
                Payout.objects
                .select_for_update()
                .get(id=payout_id)
            )

            if payout.status != Payout.Status.PROCESSING:
                return

            assert_valid_transition(payout.status, Payout.Status.FAILED)

            payout.status = Payout.Status.FAILED
            payout.failure_reason = "Bank failure"
            payout.save(update_fields=[
                        "status", "failure_reason", "updated_at"])

            LedgerEntry.objects.create(
                merchant=payout.merchant,
                amount=payout.amount,
                entry_type=LedgerEntry.EntryType.CREDIT,
                payout=payout,
                reference=f"payout_refund:{payout.id}",
            )

    elif result == "retry":
        with transaction.atomic():
            payout = (
                Payout.objects
                .select_for_update()
                .get(id=payout_id)
            )

            if payout.status != Payout.Status.PROCESSING:
                return

            payout.retry_count += 1
            payout.last_attempt_at = timezone.now()

            current_retry = payout.retry_count

            if current_retry >= 3:
                payout.status = Payout.Status.FAILED
                payout.failure_reason = "Max retries exceeded"

                payout.save(update_fields=[
                    "status",
                    "failure_reason",
                    "retry_count",
                    "last_attempt_at",
                    "updated_at",
                ])

                LedgerEntry.objects.create(
                    merchant=payout.merchant,
                    amount=payout.amount,
                    entry_type=LedgerEntry.EntryType.CREDIT,
                    payout=payout,
                    reference=f"payout_refund:{payout.id}",
                )
                return

            payout.save(update_fields=[
                "retry_count",
                "last_attempt_at",
                "updated_at",
            ])

            delay_seconds = 30 * (2 ** (current_retry - 1))

        process_payout.apply_async(
            args=[payout_id],
            countdown=delay_seconds
        )
