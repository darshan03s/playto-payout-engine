# Playto Payout Engine

A minimal payout engine that simulates how money moves from a platform to merchants.
Built as part of the Playto Founding Engineer Challenge.

---

## Overview

This system allows merchants to:

- View their balance (derived from ledger entries)
- Request payouts to their bank accounts
- Track payout status (pending → processing → completed/failed)

The system is designed to handle:

- Concurrency (no double-spend)
- Idempotency (safe retries)
- Ledger correctness (money invariant always holds)
- Background processing (async payout lifecycle)

---

## Tech Stack

### Backend

- Python
- Django + Django REST Framework
- PostgreSQL
- Celery (background jobs)
- Redis (broker)
- Docker

### Frontend

- Next.js (App Router)
- TypeScript
- Tailwind CSS
- Radix UI

---

## Features

### 1. Ledger-based Balance

- All amounts stored in **paise (integers)**
- No floats used
- Balance derived as:

```
balance = credits - debits
```

- Ledger invariant always holds

---

### 2. Payout API (Idempotent)

- Endpoint: `/api/v1/payouts`
- Requires:
  - `X-Merchant-ID`
  - `Idempotency-Key` (UUID)

Guarantees:

- Same key → same response
- No duplicate payouts
- Handles in-flight requests safely

---

### 3. Concurrency Safety

- Uses database-level locking (`SELECT FOR UPDATE`)
- Prevents overdrawing balance under parallel requests

---

### 4. Payout Processing (Async)

- Background worker processes payouts
- Simulated outcomes:
  - 70% success
  - 20% failure
  - 10% retry

Retry system:

- Exponential backoff
- Max 3 attempts
- Refund on failure

---

### 5. State Machine Enforcement

Valid transitions:

```
pending → processing → completed
pending → processing → failed
```

Invalid transitions are rejected.

---

### 6. Merchant Dashboard

- Available balance
- Held balance (pending/processing payouts)
- Payout history
- Recent ledger activity
- Request payout flow

---

## Project Structure

```
backend/
  core/                # Django project config
  payoutengine/        # Core business logic
  services/            # Ledger + payout logic
  tasks.py             # Celery workers
  docker-compose.yml
  docker-compose.dev.yml

frontend/
  app/                 # Next.js App Router
  components/          # UI components
```

---

## Running Locally (Development)

### Prerequisites

- Docker
- Node.js
- pnpm

---

### Start Backend

Run:

```
docker compose -f docker-compose.dev.yml up --build
```

What this does:

- Builds backend image
- Starts:
  - PostgreSQL
  - Redis
  - Django server
  - Celery worker
  - Celery beat

- Runs migrations
- Seeds initial data

Backend runs at:

```
http://localhost:8000
```

---

### Start Frontend

Navigate to frontend directory and run:

```
pnpm dev
```

What this does:

- Starts Next.js development server
- Enables hot reload

Frontend runs at:

```
http://localhost:3000
```

---

## Seed Data

On startup, the system creates:

- Sample merchants
- Bank accounts
- Ledger credits/debits

This allows immediate testing of payout flows.

---

## Key Design Decisions

- **Ledger-first system**: balance is never stored, always derived
- **Immediate debit model**: funds are deducted at payout request time
- **Idempotency at DB layer**: prevents duplicate side effects
- **DB-level locking**: ensures correctness under concurrency

---

## Testing

Includes tests for:

- Idempotency (duplicate requests)
- Concurrency (parallel payouts)
- Ledger invariant (credits - debits)

Run tests inside backend container:

```
docker exec -it playto_web python manage.py test
```
