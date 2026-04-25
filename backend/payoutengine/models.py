import uuid
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Merchant(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class BankAccount(BaseModel):
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="bank_accounts", db_index=True)
    account_number = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.merchant.name} - {self.account_number}"


class LedgerEntry(BaseModel):
    class EntryType(models.TextChoices):
        CREDIT = "credit"
        DEBIT = "debit"

    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="ledger_entries", db_index=True)

    amount = models.BigIntegerField()

    entry_type = models.CharField(max_length=10, choices=EntryType.choices)

    payout = models.ForeignKey(
        "Payout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries"
    )

    reference = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["merchant", "entry_type"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="ledger_amount_positive"
            )
        ]


class IdempotencyKey(BaseModel):
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="idempotency_keys", db_index=True)

    key = models.UUIDField()

    response_data = models.JSONField(null=True, blank=True)

    payout = models.OneToOneField(
        "Payout",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="idempotency_record"
    )

    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "key"],
                name="unique_idempotency_per_merchant"
            )
        ]
        indexes = [
            models.Index(fields=["merchant", "key"]),
            models.Index(fields=["expires_at"]),
        ]


class Payout(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="payouts", db_index=True)

    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT)

    amount = models.BigIntegerField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    retry_count = models.IntegerField(default=0)

    last_attempt_at = models.DateTimeField(null=True, blank=True)

    failure_reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["merchant", "status"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="payout_amount_positive"
            )
        ]
