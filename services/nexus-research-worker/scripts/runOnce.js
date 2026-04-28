/**
 * scripts/runOnce.js — Process exactly one research_collect job then exit.
 * Usage: node scripts/runOnce.js
 */

import { runOnce } from '../src/loop.js';

const found = await runOnce();
process.exit(found ? 0 : 1);
