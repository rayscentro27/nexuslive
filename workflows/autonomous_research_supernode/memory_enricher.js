// ── Memory enricher — thin adapter over Phase 7 implementation ────────────────

import { enrichMemory as _enrichMemory } from "../research_ingestion/memory_enricher.js";

export async function enrichMemory(payload, classification, extracted) {
  const adapted = {
    ...payload,
    // Phase 7 memory enricher reads transcript_text
    transcript_text: payload.content_text ?? payload.transcript_text ?? "",
  };
  return _enrichMemory(adapted, classification, extracted);
}
