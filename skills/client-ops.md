# Skill: Client Operations — Onboarding & Management

## The Client Pipeline
When a new user registers at goclearonline.cc:
1. Supabase `auth.users` INSERT → `handle_new_user()` trigger fires
2. `user_profiles` row created (role='client', plan='free')
3. `emit_client_registered()` trigger fires → `system_events` INSERT
4. `autonomy_worker` picks up `client_registered` event within 30 seconds
5. `event_dispatcher` routes to: credit agent, funding agent, capital agent,
   communication agent, business agent
6. Agents create tasks, send welcome communications, score the client

## Client Data Location
- **Supabase table `user_profiles`**: id, full_name, email, role, subscription_plan, created_at
- **Supabase table `system_events`**: event history for every client action
- **Supabase table `tasks`**: all agent-created tasks tied to client_id

## Checking a Client's Status
```sql
SELECT * FROM user_profiles WHERE email = 'client@example.com';
SELECT * FROM system_events WHERE payload->>'client_id' = '<uuid>' ORDER BY created_at DESC LIMIT 10;
SELECT * FROM tasks WHERE metadata->>'client_id' = '<uuid>' AND status = 'pending';
```

## Subscription Plans
- **free**: Basic access, limited features
- **pro**: Full access to AI tools and dashboard
- **enterprise**: Custom pricing, dedicated support

## Stripe Integration
- Live Stripe key active on goclearonline.cc
- Webhook secret: stored in Netlify env as STRIPE_WEBHOOK_SECRET
- Events to handle: `checkout.session.completed`, `customer.subscription.updated`,
  `customer.subscription.deleted`
- On successful payment → update `user_profiles.subscription_plan` in Supabase

## Communication Rules
- All automated client emails go through the Gmail pipeline (goclearonline@gmail.com)
- Telegram alerts for operator go to chat ID 1288928049 via @NexusHermbot
- Do not send Telegram messages directly to clients — email only
- Always address clients by their `full_name` from user_profiles

## Upsell Signal
Oracle agent finding: free users who connect analytics within 48h of signup
convert to paid at 34% vs 6%. Trigger a targeted follow-up for users who
haven't connected analytics by hour 47.
