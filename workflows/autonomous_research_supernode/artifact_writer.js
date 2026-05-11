// ── Artifact writer — thin adapter over Phase 7 implementation ────────────────
// Bridges content_text → transcript_text for the Phase 7 writer.
// ─────────────────────────────────────────────────────────────────────────────

import {
  writeArtifact as _writeArtifact,
  writeClaims as _writeClaims,
} from "../research_ingestion/artifact_writer.js";

function adapt(payload) {
  return {
    ...payload,
    // Phase 7 writer reads transcript_text for content column
    transcript_text: payload.content_text ?? payload.transcript_text ?? "",
    // Phase 7 writer reads source_name for source/channel_name columns
    source_name: payload.source_name,
  };
}

export async function writeArtifact(payload, classification, extracted) {
  return _writeArtifact(adapt(payload), classification, extracted);
}

export async function writeClaims(payload, classification, extracted) {
  return _writeClaims(adapt(payload), classification, extracted);
}
