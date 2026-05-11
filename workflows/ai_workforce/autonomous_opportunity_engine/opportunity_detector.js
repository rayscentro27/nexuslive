// -- Autonomous Opportunity Detector -----------------------------------------
// Extracts candidate opportunities from research tables and aggregates repeated
// themes into structured opportunity records.
// -----------------------------------------------------------------------------

import { normalizeOpportunitySignal, toAggregationKey } from "./opportunity_normalizer.js";

const JOB_TYPE_FILTERS = {
  opportunity_scan: null,
  grant_opportunity_scan: new Set(["grant_opportunity"]),
  service_gap_scan: new Set(["service_gap"]),
  automation_idea_scan: new Set(["automation_idea"]),
  opportunity_brief_generation: null,
};

function toText(value) {
  if (!value) return "";
  if (Array.isArray(value)) return value.join(" ");
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return "";
    }
  }
  return String(value);
}

function buildArtifactSignals(artifacts = []) {
  const rows = [];
  for (const a of artifacts) {
    const text = [
      a.title,
      a.summary,
      a.content,
      toText(a.key_points),
      toText(a.opportunity_notes),
      toText(a.action_items),
    ].filter(Boolean).join(" ");

    rows.push({
      id: a.id,
      source_kind: "artifact",
      source_topic: a.topic,
      source: a.source,
      title: a.title,
      text,
      description: a.summary,
      evidence: toText(a.key_points) || a.summary,
      confidence: a.confidence ?? 0.55,
      trace_id: a.trace_id,
      created_at: a.created_at,
    });

    for (const note of Array.isArray(a.opportunity_notes) ? a.opportunity_notes : []) {
      rows.push({
        id: a.id,
        source_kind: "artifact_note",
        source_topic: a.topic,
        source: a.source,
        title: a.title,
        text: String(note),
        description: String(note),
        evidence: a.summary ?? String(note),
        confidence: a.confidence ?? 0.6,
        trace_id: a.trace_id,
        created_at: a.created_at,
      });
    }
  }
  return rows;
}

function buildClaimSignals(claims = []) {
  return claims.map((c) => ({
    id: c.id,
    source_kind: "claim",
    source_topic: c.topic,
    source: c.source,
    title: c.claim_text,
    text: [c.claim_text, c.claim_type, c.subtheme].filter(Boolean).join(" "),
    description: c.claim_text,
    evidence: c.claim_text,
    confidence: c.confidence ?? 0.6,
    trace_id: c.trace_id,
    created_at: c.created_at,
  }));
}

function buildClusterSignals(clusters = []) {
  return clusters.map((c) => ({
    id: c.id,
    source_kind: "cluster",
    source_topic: "general_business_intelligence",
    source: c.cluster_name ?? "cluster",
    title: c.cluster_name ?? c.theme,
    text: [c.cluster_name, c.theme, c.summary, toText(c.key_terms)].filter(Boolean).join(" "),
    description: c.summary,
    evidence: [c.theme, toText(c.key_terms)].filter(Boolean).join(" | "),
    confidence: c.confidence ?? 0.55,
    trace_id: c.trace_id,
    created_at: c.created_at,
  }));
}

function buildHypothesisSignals(hypotheses = []) {
  return hypotheses.map((h) => ({
    id: h.id,
    source_kind: "hypothesis",
    source_topic: h.asset_type === "grants" ? "grant_research" : "business_opportunities",
    source: "research_hypotheses",
    title: h.hypothesis_title,
    text: [h.hypothesis_title, h.hypothesis_text, toText(h.supporting_evidence), h.market_type, h.asset_type]
      .filter(Boolean)
      .join(" "),
    description: h.hypothesis_text,
    evidence: toText(h.supporting_evidence),
    confidence: Number(h.plausibility_score ?? h.novelty_score ?? 0.55) / 10,
    trace_id: h.trace_id,
    created_at: h.created_at,
  }));
}

function buildCoverageGapSignals(gaps = []) {
  return gaps.map((g) => ({
    id: g.id,
    source_kind: "coverage_gap",
    source_topic: "general_business_intelligence",
    source: "coverage_gaps",
    title: `${g.gap_type ?? "gap"} gap`,
    text: [g.gap_type, g.asset_type, g.description, g.notes, g.severity].filter(Boolean).join(" "),
    description: g.description,
    evidence: [g.description, g.notes].filter(Boolean).join(" | "),
    confidence: g.severity === "high" ? 0.8 : g.severity === "low" ? 0.45 : 0.6,
    severity: g.severity,
    created_at: g.created_at,
  }));
}

function aggregateSignals(normalizedSignals = []) {
  const map = new Map();

  for (const signal of normalizedSignals) {
    const key = toAggregationKey(signal);
    const existing = map.get(key);

    if (!existing) {
      map.set(key, {
        ...signal,
        signal_count: 1,
        sources: [signal.source],
        source_kinds: [signal.source_kind],
        evidence_points: [signal.evidence_summary],
        confidence_sum: signal.confidence,
      });
      continue;
    }

    existing.signal_count += 1;
    existing.confidence_sum += signal.confidence;

    if (!existing.sources.includes(signal.source)) existing.sources.push(signal.source);
    if (!existing.source_kinds.includes(signal.source_kind)) existing.source_kinds.push(signal.source_kind);

    if (signal.evidence_summary && existing.evidence_points.length < 5) {
      existing.evidence_points.push(signal.evidence_summary);
    }

    if (new Date(signal.created_at).getTime() > new Date(existing.created_at).getTime()) {
      existing.created_at = signal.created_at;
      existing.trace_id = signal.trace_id ?? existing.trace_id;
    }

    if (signal.urgency === "high") existing.urgency = "high";
    if (existing.urgency !== "high" && signal.urgency === "medium") existing.urgency = "medium";
  }

  return [...map.values()].map((row) => ({
    ...row,
    confidence: Math.max(0, Math.min(1, row.confidence_sum / Math.max(row.signal_count, 1))),
    evidence_summary: row.evidence_points.slice(0, 3).join(" | "),
  }));
}

function applyJobTypeFilter(opportunities, jobType) {
  const allowedTypes = JOB_TYPE_FILTERS[jobType] ?? null;
  if (!allowedTypes) return opportunities;
  return opportunities.filter((o) => allowedTypes.has(o.opportunity_type));
}

export function detectOpportunities(dataset, { job_type = "opportunity_scan", max_signals = 600 } = {}) {
  const rawSignals = [
    ...buildArtifactSignals(dataset.research_artifacts),
    ...buildClaimSignals(dataset.research_claims),
    ...buildClusterSignals(dataset.research_clusters),
    ...buildHypothesisSignals(dataset.research_hypotheses),
    ...buildCoverageGapSignals(dataset.coverage_gaps),
  ].slice(0, max_signals);

  const normalized = rawSignals.map(normalizeOpportunitySignal);
  const aggregated = aggregateSignals(normalized);
  return applyJobTypeFilter(aggregated, job_type);
}
