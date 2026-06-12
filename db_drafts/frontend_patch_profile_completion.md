# Frontend / API Patch — Profile Completion (DRAFT / REVIEW ONLY — not applied)

Repo: `~/nexuslive` (React + Vite). These are the minimal changes so completing
a profile actually **persists** and triggers the notification. Nothing here is
applied; styling/routes/auth unchanged.

## Patch 1 — `src/lib/db.ts` : add an atomic completion call (uses the new RPC)
Add next to the existing `updateProfile` (around line 184):

```ts
// Atomic profile completion: persists onboarding_complete + readiness_score,
// and the DB trigger creates the portal notification. Self-only (RPC uses auth.uid()).
export async function completeProfile(readinessScore?: number) {
  const { data, error } = await supabase.rpc('complete_user_profile', {
    p_readiness_score: readinessScore ?? null,
  });
  return { data: data as UserProfile | null, error };
}
```

Fallback (if RPC not yet deployed) — keep `updateProfile` but ensure the flag is set:
```ts
// await updateProfile(userId, { onboarding_complete: true, readiness_score: score });
```

## Patch 2 — profile/onboarding save handler (e.g. `src/components/Account.tsx`)
Where the profile "save/finish" succeeds today (it currently calls `updateProfile`
WITHOUT `onboarding_complete`), call completion and gate the UI on success:

```ts
const { data, error } = await completeProfile(computedReadiness);
if (error) {
  setError('Could not save your profile. Please try again.'); // surface failure
  return;                                                      // do NOT show "complete"
}
setProfile(data);            // refresh local state from the persisted row
setShowComplete(true);       // only after backend confirms
// no manual notification insert here — the DB trigger handles it (avoids duplicates)
```

Key rule: **never set the UI to "complete" unless the backend write succeeded.**
The previous bug was UI-only "completion" with no persisted `onboarding_complete`.

## Patch 3 — `src/contexts/NotificationContext.tsx` : allow the new type to render
Add `'onboarding'` to the notification `type` union (line ~8) so toasts/icons render:

```ts
type: 'action' | 'system' | 'ai' | 'urgent' | 'message'
    | 'funding' | 'grant' | 'trading' | 'subscription' | 'onboarding';
```
(DB column is free-text NOT NULL DEFAULT 'system', so this is display-only.)

## Notes
- Do NOT add a client-side `createNotification` for completion — the trigger is the
  single source of truth and is idempotent (prevents duplicates on repeated save).
- Tenant/auth unchanged: RPC runs as the authenticated user against their own row.
- Optional admin/Ray alert: a separate (already-existing) admin path can read
  new `onboarding` notifications; no external email is added here.
