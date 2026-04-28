import random
from payoutengine.models import Merchant, LedgerEntry, BankAccount, Payout


def run():
    Payout.objects.all().delete()
    LedgerEntry.objects.all().delete()

    merchant_names = ["Nimbus Labs", "Orion Digital"]

    merchants = []

    # ── Ensure merchants + bank accounts exist ──
    for name in merchant_names:
        merchant, created = Merchant.objects.get_or_create(name=name)

        # ensure at least 2 bank accounts
        existing_accounts = merchant.bank_accounts.count()

        if existing_accounts < 2:
            for _ in range(2 - existing_accounts):
                BankAccount.objects.create(
                    merchant=merchant,
                    account_number=str(random.randint(10**11, 10**12 - 1))
                )

        merchants.append(merchant)

    # ── Always add new ledger entries ──
    for merchant in merchants:
        # credits (bigger amounts)
        for _ in range(5):
            amount = random.randint(10000, 50000)
            LedgerEntry.objects.create(
                merchant=merchant,
                amount=amount,
                entry_type=LedgerEntry.EntryType.CREDIT,
                reference="seed_credit"
            )

        # debits
        for _ in range(2):
            amount = random.randint(5000, 20000)
            LedgerEntry.objects.create(
                merchant=merchant,
                amount=amount,
                entry_type=LedgerEntry.EntryType.DEBIT,
                reference="seed_debit"
            )

    print("Seeding completed")
