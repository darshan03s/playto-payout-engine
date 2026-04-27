'use client'

import { api } from '@/lib/utils'
import { Merchant, Payout } from '@/types'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell
} from '@/components/ui/table'
import Link from 'next/link'

const statusColor: Record<Payout['status'], string> = {
  pending: 'text-yellow-600',
  processing: 'text-blue-600',
  completed: 'text-green-600',
  failed: 'text-red-600'
}

function formatAmount(paise: number) {
  return `₹${(paise / 100).toFixed(2)}`
}

const MerchantData = ({ merchantId }: { merchantId: string }) => {
  const [merchant, setMerchant] = useState<Merchant | null>(null)

  const fetchData = async () => {
    const res = await fetch(`${api()}/api/merchant/${merchantId}`)
    const json = await res.json()
    setMerchant(json.merchant)
  }

  useEffect(() => {
    fetchData()

    const interval = setInterval(fetchData, 5000)

    return () => clearInterval(interval)
  }, [])

  if (!merchant) return null

  return (
    <div className="min-h-[calc(100vh-48px)] flex justify-center p-6">
      <div className="w-full max-w-4xl space-y-8">
        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">{merchant.merchantName}</h1>
              <div className="mt-2 space-y-1">
                <p className="text-sm text-muted-foreground">Available</p>
                <p className="text-2xl font-bold">{formatAmount(merchant.availableBalance)}</p>

                <p className="text-sm text-muted-foreground mt-2">Held</p>
                <p className="text-lg font-medium">{formatAmount(merchant.heldBalance)}</p>
              </div>
            </div>
            <Link href={`/merchant/${merchantId}/payout`}>
              <Button size="lg">Request Payout</Button>
            </Link>
          </div>
        </div>

        <h2 className="text-lg font-semibold mb-4">Payouts</h2>

        {merchant.payouts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-muted-foreground">No payouts yet</p>
            <p className="text-muted-foreground text-sm mt-1">
              Payouts you request will appear here.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Payout ID</TableHead>
                <TableHead>Requested At</TableHead>
                <TableHead>Bank Account</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {merchant.payouts.map((p) => (
                <TableRow key={p.payoutId}>
                  <TableCell className="font-mono text-xs">{p.payoutId}</TableCell>
                  <TableCell>{new Date(p.requestedAt).toLocaleString()}</TableCell>
                  <TableCell>{p.bankAccount}</TableCell>
                  <TableCell className="text-right">{formatAmount(p.amount)}</TableCell>
                  <TableCell>
                    <span className={`capitalize font-medium ${statusColor[p.status]}`}>
                      {p.status}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}

export default MerchantData
