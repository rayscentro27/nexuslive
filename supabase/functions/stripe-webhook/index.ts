import Stripe from 'https://esm.sh/stripe@17?target=deno';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY') ?? '', {
  apiVersion: '2024-12-18.acacia',
  httpClient: Stripe.createFetchHttpClient(),
});

const supabase = createClient(
  Deno.env.get('SUPABASE_URL') ?? '',
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
);

const PLAN_MAP: Record<string, string> = {
  [Deno.env.get('STRIPE_PRICE_PRO') ?? '']:   'pro',
  [Deno.env.get('STRIPE_PRICE_ELITE') ?? '']: 'elite',
};

Deno.serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 });
  }

  const body = await req.text();
  const sig  = req.headers.get('stripe-signature') ?? '';
  const secret = Deno.env.get('STRIPE_WEBHOOK_SECRET') ?? '';

  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(body, sig, secret);
  } catch (err) {
    console.error('Signature verification failed:', err);
    return new Response(`Webhook Error: ${err.message}`, { status: 400 });
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;
        const userId  = session.client_reference_id;
        const email   = session.customer_email;

        let priceId = (session as any).line_items?.data?.[0]?.price?.id;
        if (!priceId && session.subscription) {
          const sub = await stripe.subscriptions.retrieve(session.subscription as string, {
            expand: ['items.data.price'],
          });
          priceId = sub.items.data[0]?.price?.id;
        }

        const plan = PLAN_MAP[priceId ?? ''] || 'pro';

        if (!userId) {
          console.error('No client_reference_id on session', session.id);
          break;
        }

        const { error } = await supabase.from('user_subscriptions').upsert({
          user_id:                userId,
          email:                  email,
          plan,
          stripe_customer_id:     session.customer as string,
          stripe_subscription_id: session.subscription as string,
          stripe_price_id:        priceId,
          status:                 'active',
          current_period_start:   new Date().toISOString(),
          updated_at:             new Date().toISOString(),
        }, { onConflict: 'user_id' });

        if (error) throw error;
        console.log(`Activated: user=${userId} plan=${plan}`);
        break;
      }

      case 'customer.subscription.updated': {
        const sub     = event.data.object as Stripe.Subscription;
        const priceId = sub.items.data[0]?.price?.id;
        const plan    = PLAN_MAP[priceId ?? ''] || 'pro';

        const { error } = await supabase.from('user_subscriptions').update({
          plan,
          stripe_price_id:    priceId,
          status:             sub.status,
          current_period_end: new Date(sub.current_period_end * 1000).toISOString(),
          updated_at:         new Date().toISOString(),
        }).eq('stripe_subscription_id', sub.id);

        if (error) throw error;
        console.log(`Updated: sub=${sub.id} plan=${plan}`);
        break;
      }

      case 'customer.subscription.deleted': {
        const sub = event.data.object as Stripe.Subscription;

        const { error } = await supabase.from('user_subscriptions').update({
          plan:       'free',
          status:     'canceled',
          updated_at: new Date().toISOString(),
        }).eq('stripe_subscription_id', sub.id);

        if (error) throw error;
        console.log(`Canceled: sub=${sub.id}`);
        break;
      }

      default:
        console.log(`Unhandled: ${event.type}`);
    }
  } catch (err) {
    console.error('Handler error:', err);
    return new Response('Internal error', { status: 500 });
  }

  return new Response(JSON.stringify({ received: true }), {
    headers: { 'Content-Type': 'application/json' },
  });
});
