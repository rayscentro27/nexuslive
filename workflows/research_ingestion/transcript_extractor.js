import "dotenv/config";
import { execSync } from "child_process";
import { existsSync, readFileSync, readdirSync, mkdirSync } from "fs";
import path from "path";
import { randomUUID } from "crypto";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH / INGESTION ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const DROP_IN_DIR = "./drop_in";
const TMP_BASE = "/tmp/nexus_transcripts";

const SUPPORTED_TOPICS = [
  "trading",
  "credit_repair",
  "grant_research",
  "business_opportunities",
  "crm_automation",
  "general_business_intelligence",
];

/**
 * Parse YouTube VTT subtitle text into plain text.
 * Strips timestamps, cue IDs, HTML tags, and deduplicates repeated lines.
 */
function parseVtt(vttText) {
  const seen = new Set();
  const lines = vttText.split("\n");
  const result = [];

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("WEBVTT")) continue;
    if (line.includes("-->")) continue;
    if (/^\d+$/.test(line)) continue;
    if (/^<\d\d:\d\d/.test(line)) continue;

    // Strip HTML tags (e.g. <c>, </c>, <00:00:01.000>)
    const clean = line.replace(/<[^>]+>/g, "").trim();
    if (!clean || seen.has(clean)) continue;
    seen.add(clean);
    result.push(clean);
  }

  return result.join(" ");
}

/**
 * Try to resolve yt-dlp binary path.
 */
function findYtDlp() {
  for (const cmd of ["yt-dlp", "/usr/local/bin/yt-dlp", "/opt/homebrew/bin/yt-dlp"]) {
    try {
      execSync(`which ${cmd} 2>/dev/null || command -v ${cmd} 2>/dev/null`, { timeout: 3000 });
      return cmd;
    } catch {
      // try next
    }
  }
  return null;
}

/**
 * Extract transcripts from a YouTube channel or video URL using yt-dlp.
 *
 * @param {Object} source - { url, name, topic, max_videos? }
 * @returns {Promise<Array>} normalized transcript payloads
 */
export async function extractFromYoutube(source) {
  const { url, name, topic, max_videos = 3 } = source;
  const ytDlp = findYtDlp();

  if (!ytDlp) {
    console.warn(`[extractor] yt-dlp not found — skipping ${name}. Install: pip install yt-dlp`);
    return [];
  }

  const tmpDir = `${TMP_BASE}_${Date.now()}`;
  mkdirSync(tmpDir, { recursive: true });

  const results = [];

  // Step 1: Get list of video URLs from channel (or treat as single video)
  let videoUrls = [];
  try {
    const listOut = execSync(
      `${ytDlp} --flat-playlist --get-url --playlist-end ${max_videos} "${url}" 2>/dev/null`,
      { timeout: 120000, encoding: "utf8" }
    );
    videoUrls = listOut.trim().split("\n").filter(Boolean);
  } catch {
    // May be a single video URL — try directly
    videoUrls = [url];
  }

  // Step 2: Process each video
  for (const videoUrl of videoUrls) {
    const videoTmp = `${tmpDir}/${randomUUID()}`;
    mkdirSync(videoTmp, { recursive: true });

    try {
      // Get video metadata
      const metaOut = execSync(
        `${ytDlp} --dump-json --skip-download "${videoUrl}" 2>/dev/null`,
        { timeout: 30000, encoding: "utf8" }
      );
      const meta = JSON.parse(metaOut.trim());

      // Download auto-captions (English, VTT format)
      try {
        execSync(
          `${ytDlp} --write-auto-subs --sub-lang en --sub-format vtt --skip-download -o "${videoTmp}/%(id)s" "${videoUrl}" 2>/dev/null`,
          { timeout: 60000 }
        );
      } catch {
        // Also try manual subtitles as fallback
        try {
          execSync(
            `${ytDlp} --write-subs --sub-lang en --sub-format vtt --skip-download -o "${videoTmp}/%(id)s" "${videoUrl}" 2>/dev/null`,
            { timeout: 30000 }
          );
        } catch {
          // No subtitles available
        }
      }

      // Find any VTT file downloaded
      const vttFiles = readdirSync(videoTmp).filter(f => f.endsWith(".vtt"));
      if (!vttFiles.length) {
        console.log(`[extractor] No transcript available for: "${meta.title ?? videoUrl}" — skipping.`);
        continue;
      }

      const vttText = readFileSync(path.join(videoTmp, vttFiles[0]), "utf8");
      const transcript_text = parseVtt(vttText);

      if (transcript_text.length < 150) {
        console.log(`[extractor] Transcript too short (<150 chars) for: "${meta.title}" — skipping.`);
        continue;
      }

      // Normalize upload_date: "20250115" → "2025-01-15"
      const rawDate = meta.upload_date ?? "";
      const published_at = rawDate.length === 8
        ? `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}`
        : new Date().toISOString().slice(0, 10);

      results.push({
        source_name: name,
        source_type: "youtube_channel",
        source_url: videoUrl,
        topic,
        title: meta.title ?? videoUrl,
        transcript_text,
        published_at,
        trace_id: randomUUID(),
      });

      console.log(`[extractor] Extracted transcript: "${meta.title}" (${transcript_text.length} chars)`);

    } catch (err) {
      console.log(`[extractor] Skipping ${videoUrl}: ${err.message.slice(0, 80)}`);
    }
  }

  return results;
}

/**
 * Load transcript files from the drop_in/ folder.
 * Supports .txt, .md, .vtt files.
 * Topic inferred from filename prefix (e.g. credit_repair_transcript.txt).
 *
 * @param {string|null} topicFilter - only return files matching this topic
 * @returns {Array} normalized transcript payloads
 */
export function loadDropIns(topicFilter = null) {
  if (!existsSync(DROP_IN_DIR)) {
    console.log(`[extractor] drop_in/ directory not found — no local transcripts loaded.`);
    return [];
  }

  const files = readdirSync(DROP_IN_DIR).filter(f =>
    f.endsWith(".txt") || f.endsWith(".vtt") || f.endsWith(".md")
  );

  if (!files.length) {
    console.log("[extractor] No transcript files found in drop_in/");
    return [];
  }

  const results = [];

  for (const file of files) {
    const filePath = path.join(DROP_IN_DIR, file);
    const rawContent = readFileSync(filePath, "utf8");
    const transcript_text = file.endsWith(".vtt") ? parseVtt(rawContent) : rawContent;

    // Infer topic from filename prefix: "credit_repair_..."
    const topicMatch = SUPPORTED_TOPICS.find(t => file.startsWith(t));
    const topic = topicMatch ?? "general_business_intelligence";

    if (topicFilter && topic !== topicFilter) continue;

    if (transcript_text.trim().length < 50) {
      console.log(`[extractor] drop_in file too short: ${file} — skipping.`);
      continue;
    }

    const title = file.replace(/\.[^.]+$/, "").replace(/_/g, " ");

    results.push({
      source_name: file,
      source_type: "local_file",
      source_url: filePath,
      topic,
      title,
      transcript_text,
      published_at: new Date().toISOString().slice(0, 10),
      trace_id: randomUUID(),
    });

    console.log(`[extractor] Loaded drop-in: "${title}" (topic=${topic})`);
  }

  return results;
}
