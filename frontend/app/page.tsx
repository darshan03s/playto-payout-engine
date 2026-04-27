import { buttonVariants } from '@/components/ui/button'
import { api } from '@/lib/utils'
import Link from 'next/link'

interface Merchant {
  merchantId: string
  merchantName: string
}

const Page = async () => {
  const res = await fetch(`${api()}/api/merchants`)

  if (!res.ok) {
    return (
      <div className="h-screen flex items-center justify-center">Could not fetch merchants</div>
    )
  }

  const json = await res.json()

  const merchants = json.merchants as Merchant[]

  return (
    <div className="h-[calc(100vh-48px)] flex items-center justify-center">
      <div className="flex flex-col gap-4">
        <h1 className="text-3xl font-bold">Merchants</h1>
        {merchants.map((m) => (
          <Link
            key={m.merchantId}
            href={`/merchant/${m.merchantId}`}
            className={buttonVariants({ variant: 'secondary' })}
          >
            {m.merchantName}
          </Link>
        ))}
      </div>
    </div>
  )
}

export default Page
