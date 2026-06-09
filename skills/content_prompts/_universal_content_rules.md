# Universal Content Rules
_Every prompt in this library inherits these rules. They override anything that conflicts._

## Autonomy vs. approval
- **Nexus MAY do autonomously:** research, study sources/transcripts, create source_extractions,
  generate ideas, score opportunities, draft scripts/posts/newsletters, build packets, render **draft**
  audio/video, score quality, route to the right prompt, update the Content Workspace Board, generate
  approval cards, write Telegram digests, and **recommend** next actions.
- **Ray approval is REQUIRED before:** publishing, scheduling, posting publicly, sending emails/newsletters,
  spending money, using paid APIs/tools, changing credentials, production deployments, database migrations,
  live trading/broker orders, or moving money. Any external/public action waits for Ray.
- The only upload path is `scripts/social_publish_executor.py`; it is **disabled by default**
  (`NEXUS_PUBLISH_EXECUTOR_ENABLED` unset). Prompts must never enable it or change its gates.

## Truth & compliance
- **No unsupported claims.** Every factual claim must trace to a source/source_extraction.
- **No guarantees** of funding, credit approval, credit repair, trading profits, income, or outcomes.
  Ban phrases like "get approved", "guaranteed", "fast results", "make $X".
- **Educational-only disclaimer** where relevant (finance/credit/trading): "Educational only — not
  financial advice. No guarantees."
- **Affiliate disclosure required** whenever affiliate links/programs are involved, in BOTH the on-screen
  CTA and the description/body: "This content may include affiliate links. If you use a link,
  Nexus/GoClearOnline may earn a commission at no extra cost to you."

## Imagery & posting hygiene
- **Avoid misleading wealth/luxury imagery** (cash fans, exotic cars, mansions implying easy money).
- Use clean, on-brand, faceless/illustrative visuals; no real brand marks, no photoreal faces by default.
- **Avoid spam posting** — no high-frequency near-duplicate posts; respect platform norms and cadence.

## Output discipline
- **Always output structured artifacts** (markdown packet / scene JSON / metadata block), never a raw dump.
- **Always create or update a Content Workspace Board card** for the work (`content_board_add.py` /
  `content_board_update.py` — create-or-merge; never clobber existing data; never rebuild the board).
- **Always generate an approval card** for publish-ready assets (`create_content_approval_card.py`,
  scope `review`/`unlisted` — request only, never executes).
- **Score every artifact** with `content_quality_rubric.md`. Content **below threshold (< 7/10) goes to
  `Improve / Retry`, NOT to `Needs Ray Review`.** Do not waste Ray's review on weak drafts.

## Secrets & data
- Never print, embed, or commit secrets, tokens, or `.env`. Reference credential **names only**.
- Never include executable publish/post/upload commands as actions to auto-run; show them only as the
  gated "if Ray approves" next step.

## Safety invariants (do not violate)
1. No upload · no post · no schedule · no auto-send.
2. Executor disabled by default; gates in `social_publish_executor.py` unchanged.
3. Drafts default to unlisted; v4 stays unlisted only; nothing auto-public.
4. No paid APIs / no autonomous spend; existing videos/uploads never modified or deleted.
