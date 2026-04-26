import { loadStripe } from '@stripe/stripe-js';

const STRIPE_PUBLISHABLE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '';

export const stripePromise = loadStripe(STRIPE_PUBLISHABLE_KEY);

export interface PlanConfig {
  id: string;
  name: string;
  price: number;
  interval: 'month' | 'year';
  stripePriceId: string;
  commissionRate: number;
}

export const DEFAULT_PLANS: PlanConfig[] = [
  { id: 'free', name: 'Free', price: 0, interval: 'month', stripePriceId: '', commissionRate: 0 },
  { id: 'pro', name: 'Pro', price: 50, interval: 'month', stripePriceId: import.meta.env.VITE_STRIPE_PRICE_PRO || '', commissionRate: 0.10 },
  { id: 'elite', name: 'Elite', price: 100, interval: 'month', stripePriceId: import.meta.env.VITE_STRIPE_PRICE_ELITE || '', commissionRate: 0.10 },
];

export async function redirectToCheckout(priceId: string, userId: string, email: string) {
  const stripe = await stripePromise;
  if (!stripe || !priceId) return { error: 'Stripe not configured' };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { error } = await (stripe as any).redirectToCheckout({
    lineItems: [{ price: priceId, quantity: 1 }],
    mode: 'subscription',
    successUrl: `${window.location.origin}/dashboard?subscription=success`,
    cancelUrl: `${window.location.origin}/pricing`,
    customerEmail: email,
    clientReferenceId: userId,
  });

  return { error: error?.message };
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

export function calculateCommission(fundingAmount: number, rate: number = 0.10): number {
  return fundingAmount * rate;
}
