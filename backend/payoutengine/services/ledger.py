from django.db.models import Sum, Case, When, IntegerField, Value
from django.db.models.functions import Coalesce
from payoutengine.models import LedgerEntry
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
