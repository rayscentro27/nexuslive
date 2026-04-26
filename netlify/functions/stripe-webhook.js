import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, { apiVersion: '2024-12-18.acacia' });

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY,
);

const PLAN_MAP = {
  [process.env.VITE_STRIPE_PRICE_PRO]:   'pro',
  [process.env.VITE_STRIPE_PRICE_ELITE]: 'elite',
};

async function setUserPlan(userId, plan) {
  const { error } = await supabase
    .from('user_profiles')
    .update({ subscription_plan: plan, updated_at: new Date().toISOString() })
    .eq('id', userId);
  if (error) throw new Error(`user_profiles update failed: ${error.message}`);
}

async function getUserIdFromSubscription(subscriptionId) {
  const { data } = await supabase
    .from('user_subscriptions')
    .select('user_id')
    .eq('stripe_subscription_id', subscriptionId)
    .single();
  return data?.user_id ?? null;
}

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  const sig = event.headers['stripe-signature'];
  let stripeEvent;

  try {
    stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET,
    );
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  try {
    switch (stripeEvent.type) {
      case 'checkout.session.completed': {
        const session = stripeEvent.data.object;
        const userId  = session.client_reference_id;
        const email   = session.customer_email;
        const priceId = session.line_items?.data?.[0]?.price?.id
                     ?? await getPriceIdFromSubscription(session.subscription);
        const plan    = PLAN_MAP[priceId] || 'pro';

        if (!userId) {
          console.error('No client_reference_id on session', session.id);
          break;
        }

        // Update gating source — user_profiles
        await setUserPlan(userId, plan);

        // Also record in user_subscriptions for billing history (best-effort)
        await supabase.from('user_subscriptions').upsert({
          user_id:                userId,
          email,
          plan,
          stripe_customer_id:     session.customer,
          stripe_subscription_id: session.subscription,
          stripe_price_id:        priceId,
          status:                 'active',
          current_period_start:   new Date().toISOString(),
          updated_at:             new Date().toISOString(),
        }, { onConflict: 'user_id' }).then(({ error }) => {
          if (error) console.warn('user_subscriptions upsert skipped:', error.message);
        });

        console.log(`Subscription activated — user ${userId} → ${plan}`);
        break;
      }

      case 'customer.subscription.updated': {
        const sub     = stripeEvent.data.object;
        const priceId = sub.items.data[0]?.price?.id;
        const plan    = PLAN_MAP[priceId] || 'pro';
        const userId  = await getUserIdFromSubscription(sub.id);

        // Update user_profiles if we can resolve the user
        if (userId) await setUserPlan(userId, plan);

        // Update billing record
        await supabase.from('user_subscriptions').update({
          plan,
          stripe_price_id:      priceId,
          status:               sub.status,
          current_period_start: new Date(sub.current_period_start * 1000).toISOString(),
          current_period_end:   new Date(sub.current_period_end   * 1000).toISOString(),
          updated_at:           new Date().toISOString(),
        }).eq('stripe_subscription_id', sub.id).then(({ error }) => {
          if (error) console.warn('user_subscriptions update skipped:', error.message);
        });

        console.log(`Subscription updated — ${sub.id} → ${plan} (${sub.status})`);
        break;
      }

      case 'customer.subscription.deleted': {
        const sub    = stripeEvent.data.object;
        const userId = await getUserIdFromSubscription(sub.id);

        if (userId) await setUserPlan(userId, 'free');

        await supabase.from('user_subscriptions').update({
          plan: 'free', status: 'canceled', updated_at: new Date().toISOString(),
        }).eq('stripe_subscription_id', sub.id).then(({ error }) => {
          if (error) console.warn('user_subscriptions cancel skipped:', error.message);
        });

        console.log(`Subscription canceled — ${sub.id}, user downgraded to free`);
        break;
      }

      default:
        console.log(`Unhandled event type: ${stripeEvent.type}`);
    }
  } catch (err) {
    console.error('Webhook handler error:', err);
    return { statusCode: 500, body: 'Internal error' };
  }

  return { statusCode: 200, body: JSON.stringify({ received: true }) };
};

async function getPriceIdFromSubscription(subscriptionId) {
  if (!subscriptionId) return null;
  try {
    const sub = await stripe.subscriptions.retrieve(subscriptionId, {
      expand: ['items.data.price'],
    });
    return sub.items.data[0]?.price?.id ?? null;
  } catch {
    return null;
  }
}
