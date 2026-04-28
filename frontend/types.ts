export interface Merchant {
  merchantName: string
  balance: number
  availableBalance: number
  heldBalance: number
  payouts: Payout[]
  ledger: LedgerEntry[]
}

export interface Payout {
  payoutId: string
  requestedAt: string
  bankAccount: string
  amount: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
}

export interface LedgerEntry {
  entryId: string
  type: 'credit' | 'debit'
  amount: number
  reference: string
  createdAt: string
  payoutId: string | null
}
