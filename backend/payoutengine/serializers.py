import uuid
from rest_framework import serializers
from payoutengine.models import BankAccount


class PayoutRequestSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.UUIDField()

    def validate_bank_account_id(self, value):
        """Verify bank account exists and belongs to the merchant."""
        merchant = self.context.get("merchant")
        if not merchant:
            raise serializers.ValidationError("Merchant context is required.")

        if not BankAccount.objects.filter(id=value, merchant=merchant).exists():
            raise serializers.ValidationError(
                "Bank account not found or does not belong to this merchant."
            )
        return value


class PayoutResponseSerializer(serializers.Serializer):
    payout_id = serializers.UUIDField()
    status = serializers.CharField()
    amount_paise = serializers.IntegerField()


def validate_idempotency_key(key_value: str) -> uuid.UUID:
    """Validate that the Idempotency-Key header is a valid UUID."""
    try:
        return uuid.UUID(str(key_value))
    except (ValueError, AttributeError):
        raise serializers.ValidationError(
            "Idempotency-Key must be a valid UUID."
        )
