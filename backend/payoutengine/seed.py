import random
from payoutengine.models import Merchant, LedgerEntry


def run():
    Merchant.objects.all().delete()

    merchant_names = ["Nimbus Labs", "Orion Digital"]

    merchants = []

    for name in merchant_names:
        merchant = Merchant.objects.create(name=name)
        merchants.append(merchant)

    for merchant in merchants:
        for _ in range(5):
            amount = random.randint(5000, 20000)  # ₹50 to ₹200
            LedgerEntry.objects.create(
                merchant=merchant,
                amount=amount,
                entry_type=LedgerEntry.EntryType.CREDIT,
                reference="seed_credit"
            )

        for _ in range(2):
            amount = random.randint(1000, 5000)
            LedgerEntry.objects.create(
                merchant=merchant,
                amount=amount,
                entry_type=LedgerEntry.EntryType.DEBIT,
                reference="seed_debit"
            )

    print("Seeding completed")
