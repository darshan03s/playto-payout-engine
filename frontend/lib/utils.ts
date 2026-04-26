import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function api() {
  if(process.env.NODE_ENV === 'development') {
    return process.env.NEXT_PUBLIC_BACKEND_URL_DEV
  } else {
    return process.env.NEXT_PUBLIC_BACKEND_URL_PROD
  }
}