// Adapt the Phase 7 cluster writer, which expects a batchResults array.

import { writeClusters as _writeClusters } from "../research_ingestion/cluster_writer.js";

export async function writeClusters(transcript, classification, extracted) {
  return _writeClusters([{ transcript, classification, extracted }]);
}
