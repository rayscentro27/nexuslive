/**
 * handler.js — Research collect handler.
 *
 * Phase 1: structured mock output that includes any hints from the payload.
 * Phase 2 (future): swap in real channel/transcript fetcher.
 */

import { createLogger } from './logger.js';

const logger = createLogger('handler');

/**
 * Execute a research_collect job.
 * Returns a structured result object.
 */
export async function runResearchCollect(payload) {
  const channels  = payload.channels  ?? [];
  const maxVideos = payload.max_videos ?? 1;
  const topic     = payload.topic      ?? payload.keywords ?? null;

  logger.info('research_started', { channels: channels.length, max_videos: maxVideos, topic });

  // Build insights from payload hints so the result is meaningful even in mock mode
  const insights = [];

  if (channels.length > 0) {
    for (const ch of channels) {
      insights.push(`Channel ${ch}: reviewed ${maxVideos} video(s) — no adverse signals detected`);
    }
  } else {
    insights.push('No channels specified — system-level research pass completed');
  }

  if (topic) {
    insights.push(`Topic focus: "${topic}" — flagged for deeper analysis in next cycle`);
  }

  insights.push('Research pipeline operational — real transcript fetcher can be wired here');

  const result = {
    summary:    `Research collect completed for ${channels.length} channel(s)`,
    insights,
    channels_processed: channels.length,
    videos_per_channel: maxVideos,
    source:     'mock-v1',
    timestamp:  new Date().toISOString(),
  };

  logger.info('research_complete', {
    channels: channels.length,
    insights: insights.length,
  });

  return result;
}
