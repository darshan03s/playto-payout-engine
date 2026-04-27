export interface Merchant {
  merchantName: string
  balance: number
  availableBalance: number
  heldBalance: number
  payouts: Payout[]
}

export interface Payout {
  payoutId: string
  requestedAt: string
  bankAccount: string
  amount: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
}
