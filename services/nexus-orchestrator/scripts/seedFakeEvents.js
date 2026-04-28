/**
 * scripts/seedFakeEvents.js — Insert fake system_events for local testing.
 * Usage:  node scripts/seedFakeEvents.js
 * Clears existing pending events first, then inserts one of each type.
 */

import { db } from '../src/clients/supabase.js';

// Real tenant UUID from Supabase (used for tenant-scoped events)
const TENANT_ID = 'ff88f4f5-1e15-4773-8093-ff0e95cfa9d6';

const FAKE_EVENTS = [
  {
    event_type: 'research_refresh_due',
    payload: {
      channels:   ['UCtest1', 'UCtest2'],
      max_videos: 1,
    },
  },
  {
    event_type: 'funding_profile_updated',
    payload: {
      tenant_id:       TENANT_ID,
      profile_version: 'v2',
      income:          85000,
      credit_score:    720,
    },
  },
  {
    event_type: 'credit_report_uploaded',
    payload: {
      tenant_id: TENANT_ID,
      report_id: 'rpt-abc123',
      bureau:    'Experian',
      score:     715,
    },
  },
  {
    event_type: 'strategy_submitted',
    payload: {
      strategy_id:  'strat-ema-crossover-v1',
      name:         'EMA Crossover',
      timeframe:    '1H',
      instrument:   'EUR_USD',
      entry_rule:   'EMA9 crosses above EMA21',
      exit_rule:    '1.5% stop loss, 3% take profit',
    },
  },
  {
    event_type: 'signal_detected',
    payload: {
      signal_id:   'sig-' + Date.now(),
      symbol:      'EUR_USD',
      direction:   'BUY',
      price:       1.0875,
      confidence:  78,
      source:      'tradingview',
    },
  },
];

async function seed() {
  console.log('Clearing existing pending system_events...');
  const { error: delErr } = await db
    .from('system_events')
    .delete()
    .eq('status', 'pending');

  if (delErr) {
    console.error('Delete failed:', delErr.message);
    process.exit(1);
  }

  console.log(`Inserting ${FAKE_EVENTS.length} fake events...`);
  const { data, error } = await db
    .from('system_events')
    .insert(FAKE_EVENTS.map(e => ({ ...e, status: 'pending' })))
    .select('id, event_type');

  if (error) {
    console.error('Insert failed:', error.message);
    process.exit(1);
  }

  console.log('Seeded events:');
  for (const row of data ?? []) {
    console.log(`  ${row.event_type.padEnd(30)} → ${row.id}`);
  }
  console.log('\nRun "npm start" to watch the orchestrator claim and process them.');
}

seed().catch(e => { console.error(e); process.exit(1); });
