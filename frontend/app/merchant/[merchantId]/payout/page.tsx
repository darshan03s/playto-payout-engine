import { api } from '@/lib/utils'
import PayoutClient from './payout-client'

interface PageProps {
  params: Promise<{
    merchantId: string
  }>
}

interface BankAccount {
  bankAccountId: string
  bankAccount: string
}

const Page = async ({ params }: PageProps) => {
  const { merchantId } = await params

  const res = await fetch(`${api()}/api/merchant/${merchantId}/bank-accounts`)

  if (!res.ok) {
    return (
      <div className="h-[calc(100vh-48px)] flex items-center justify-center">
        Could not fetch bank accounts
      </div>
    )
  }

  const json = await res.json()

  const bankAccounts = json.bankAccounts as BankAccount[]

  return (
    <div className="h-[calc(100vh-48px)] flex items-center justify-center">
      <PayoutClient bankAccounts={bankAccounts} />
    </div>
  )
}

export default Page
