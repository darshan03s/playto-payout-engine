from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from payoutengine.models import Merchant, LedgerEntry, BankAccount, Payout
import uuid
from threading import Thread
from django.db import connection


class BasePayoutTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.merchant = Merchant.objects.create(
            name="Test Merchant"
        )

        self.bank = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="1234567890",
        )

        # Give merchant ₹100 (10000 paise)
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount=10000,
            entry_type=LedgerEntry.EntryType.CREDIT,
        )


class IdempotencyTest(BasePayoutTest):

    def test_same_idempotency_key_creates_only_one_payout(self):
        url = "/api/v1/payouts/"
        key = str(uuid.uuid4())

        payload = {
            "amount_paise": 5000,
            "bank_account_id": str(self.bank.id)
        }

        # First request
        response1 = self.client.post(
            url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
        )

        # Second request (same key)
        response2 = self.client.post(
            url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
        )

        # ASSERTIONS
        self.assertEqual(response1.status_code, 201)

        # second can be:
        # - 200 (idempotent success)
        # - 201 (same response reused)
        # - 409 (in-flight request)
        self.assertIn(response2.status_code, [200, 201, 409])

        # if not conflict, response must match
        if response2.status_code != 409:
            self.assertEqual(response1.data, response2.data)

        # only ONE payout in DB
        self.assertEqual(Payout.objects.count(), 1)


class ConcurrencyTest(TransactionTestCase):

    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Test Merchant"
        )

        self.bank = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="1234567890",
        )

        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount=10000,
            entry_type=LedgerEntry.EntryType.CREDIT,
        )

    def test_two_parallel_payouts_only_one_succeeds(self):
        url = "/api/v1/payouts/"

        payload = {
            "amount_paise": 6000,
            "bank_account_id": str(self.bank.id)
        }

        responses = []

        def make_request():
            client = APIClient()
            try:
                res = client.post(
                    url,
                    payload,
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
                    HTTP_X_MERCHANT_ID=str(self.merchant.id),
                )
                responses.append(res)
            finally:
                connection.close()

        t1 = Thread(target=make_request)
        t2 = Thread(target=make_request)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        success_count = sum(1 for r in responses if r.status_code == 201)
        fail_count = sum(1 for r in responses if r.status_code != 201)

        self.assertEqual(success_count, 1)
        self.assertEqual(fail_count, 1)
