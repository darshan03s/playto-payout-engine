from django.db.models import Sum, Case, When, IntegerField, Value
from django.db.models.functions import Coalesce
from payoutengine.models import LedgerEntry, Payout
from django.db import models


def get_merchant_balance(merchant_id: str) -> int:
    result = (
        LedgerEntry.objects
        .filter(merchant_id=merchant_id)
        .aggregate(
            balance=Coalesce(
                Sum(
                    Case(
                        When(entry_type="credit", then="amount"),
                        When(entry_type="debit", then=-1 * models.F("amount")),
                        output_field=IntegerField(),
                    )
                ),
                Value(0)
            )
        )
    )

    return result["balance"]


def get_held_balance(merchant):
    result = (
        LedgerEntry.objects
        .filter(
            merchant=merchant,
            entry_type=LedgerEntry.EntryType.DEBIT,
            payout__status__in=[
                Payout.Status.PENDING,
                Payout.Status.PROCESSING
            ]
        )
        .aggregate(total=Coalesce(Sum("amount"), Value(0)))
    )

    return result["total"]
