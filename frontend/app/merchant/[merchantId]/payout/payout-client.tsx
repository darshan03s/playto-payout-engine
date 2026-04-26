'use client'

import { useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { api } from '@/lib/utils'

interface BankAccount {
  bankAccountId: string
  bankAccount: string
}

const PayoutClient = ({ bankAccounts }: { bankAccounts: BankAccount[] }) => {
  const idempotencyKeyRef = useRef<string | null>(null)
  const { merchantId } = useParams<{ merchantId: string }>()

  const [selectedAccountId, setSelectedAccountId] = useState('')
  const [amount, setAmount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleProceed = async () => {
    setError('')

    if (!selectedAccountId) {
      setError('Please select a bank account.')
      return
    }

    const amountNum = parseInt(amount)
    if (!amount || isNaN(amountNum) || amountNum <= 0) {
      setError('Please enter a valid amount.')
      return
    }

    const amountPaise = amountNum * 100

    // generate key ONLY once per logical request
    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current = crypto.randomUUID()
    }

    setLoading(true)

    let attempts = 0

    while (attempts < 3) {
      try {
        const res = await fetch(`${api()}/api/v1/payouts/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Merchant-ID': merchantId,
            'Idempotency-Key': idempotencyKeyRef.current!
          },
          body: JSON.stringify({
            amount_paise: amountPaise,
            bank_account_id: selectedAccountId
          })
        })

        const data = await res.json()

        if (res.ok) {
          setSuccess('Payout requested')
          idempotencyKeyRef.current = null
          setLoading(false)
          return
        }

        if (res.status === 409) {
          await new Promise((r) => setTimeout(r, 1000))
          attempts++
          continue
        }

        setError(data.error || 'Something went wrong.')
        setLoading(false)
        return
      } catch {
        attempts++
        await new Promise((r) => setTimeout(r, 1000))
      }
    }

    setError('Request failed after retries.')
    setLoading(false)
  }

  return (
    <div className="w-full max-w-md space-y-5">
      <h2 className="text-xl font-bold">Request Payout</h2>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Bank Account</label>
        <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select a bank account" />
          </SelectTrigger>
          <SelectContent>
            {bankAccounts.map((a) => (
              <SelectItem key={a.bankAccountId} value={a.bankAccountId}>
                {a.bankAccount}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Amount (₹)</label>
        <Input
          type="number"
          min="0"
          step="1"
          placeholder="0"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {success.length > 0 ? (
        <p className="text-2xl text-green-600 text-center font-bold">{success}</p>
      ) : (
        <Button className="w-full" size="lg" disabled={loading} onClick={handleProceed}>
          {loading ? 'Processing...' : 'Proceed'}
        </Button>
      )}
    </div>
  )
}

export default PayoutClient
