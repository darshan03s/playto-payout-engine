# EXPLAINER.md

## 1. The Ledger

### Balance Query

```python
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
```

### Why this model?

- All money is represented using `LedgerEntry`
- `credit` increases balance
- `debit` decreases balance

Balance is not stored, it is derived at query time:

```
balance = credits - debits
```

This ensures:

- No separate balance field that can go out of sync
- Balance is always consistent with underlying entries

Held balance is derived separately:

```python
LedgerEntry.objects
.filter(
    merchant=merchant,
    entry_type=DEBIT,
    payout__status__in=[PENDING, PROCESSING]
)
.aggregate(total=Sum("amount"))
```

---

## 2. The Lock

### Code

```python
locked_merchant = (
    Merchant.objects
    .select_for_update()
    .get(id=merchant.id)
)
```

### Explanation

- Executed inside `transaction.atomic()`
- Uses database row-level locking (`SELECT FOR UPDATE`)
- Locks the merchant row for the duration of the transaction

Flow:

1. Transaction starts
2. Merchant row is locked
3. Balance is computed using `get_merchant_balance`
4. Payout and ledger entry are created

This ensures concurrent requests cannot read and modify the same merchant balance at the same time.

---

## 3. The Idempotency

### How it works

- Each request includes an `Idempotency-Key`
- Stored in `IdempotencyKey` model with unique constraint:

  ```
  (merchant, key)
  ```

### Flow

1. Try to create a new `IdempotencyKey`
2. If successful → first request
3. If `IntegrityError`:
   - Fetch existing row using `select_for_update`
   - If `response_data` exists → return stored response
   - If `response_data` is null → request is in-flight → raise conflict

### Code

```python
IdempotencyKey.objects.create(...)
```

On conflict:

```python
existing = (
    IdempotencyKey.objects
    .select_for_update()
    .get(merchant=merchant, key=idempotency_key)
)
```

### Additional behavior

- Keys expire after 24 hours:

  ```python
  if existing.expires_at <= timezone.now():
      existing.delete()
  ```

- Response is stored in `response_data` and reused for duplicates

---

## 4. The State Machine

### Allowed transitions

```
pending → processing → completed
pending → processing → failed
```

### Enforcement

```python
def assert_valid_transition(from_state: str, to_state: str):
    allowed = {
        Payout.Status.PENDING: [Payout.Status.PROCESSING],
        Payout.Status.PROCESSING: [
            Payout.Status.COMPLETED,
            Payout.Status.FAILED,
            Payout.Status.PROCESSING
        ],
        Payout.Status.COMPLETED: [],
        Payout.Status.FAILED: [],
    }

    if to_state not in allowed.get(from_state, []):
        raise ValueError(...)
```

### Usage

Before updating status:

```python
assert_valid_transition(payout.status, Payout.Status.PROCESSING)
```

and:

```python
assert_valid_transition(payout.status, Payout.Status.COMPLETED)
```

and:

```python
assert_valid_transition(payout.status, Payout.Status.FAILED)
```

This prevents invalid transitions.

---

## 5. The AI Audit

### Problem

Initial AI-generated frontend logic:

```tsx
useEffect(() => {
  fetchData()
  const interval = setInterval(() => {
    if (merchant?.payouts.some((m) => m.status === 'processing' || m.status === 'pending')) {
      fetchData()
    }
  }, 5000)

  return () => clearInterval(interval)
}, [merchant])
```

Issue:

- `merchant` is a dependency of the effect
- `fetchData()` updates `merchant` state
- This triggers the effect again

This creates a loop:

```
fetchData → setMerchant → merchant changes → useEffect runs again → fetchData
```

Result:

- Multiple intervals are created
- API gets spammed continuously

---

### Fix

Split into two effects:

```tsx
useEffect(() => {
  fetchData()
}, [])

useEffect(() => {
  const interval = setInterval(() => {
    if (merchant?.payouts.some((m) => m.status === 'processing' || m.status === 'pending')) {
      fetchData()
    }
  }, 5000)

  return () => clearInterval(interval)
}, [merchant])
```

---

### Why this works

- First `useEffect` runs only once on mount
- Second `useEffect` handles polling
- Interval is cleaned up on dependency change
- Prevents uncontrolled re-renders and API spam

This ensures polling only happens when needed without creating multiple overlapping intervals.

---

## Additional Note: Ledger Design Choice

I use an immediate debit model.

- When payout is requested → debit entry is created immediately

- Balance reflects only spendable funds at all times

Payout request creates a debit entry immediately:

```python
LedgerEntry.objects.create(
    entry_type=DEBIT,
    payout=payout,
)
```

On failure, amount is returned:

```python
LedgerEntry.objects.create(
    entry_type=CREDIT,
    payout=payout,
)
```

Held balance is derived as:

- debits where payout is pending or processing

Held balance is not subtracted again from balance to avoid double counting.

Balance is always derived from ledger entries.
