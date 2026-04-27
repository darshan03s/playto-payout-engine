import MerchantData from './merchant-data'

interface PageProps {
  params: Promise<{
    merchantId: string
  }>
}

const Page = async ({ params }: PageProps) => {
  const { merchantId } = await params

  return <MerchantData merchantId={merchantId} />
}

export default Page
