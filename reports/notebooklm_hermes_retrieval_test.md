# NotebookLM Hermes Retrieval Test

Date: 2026-05-10

## Prompts Tested
- What NotebookLM research is ready?
- Summarize NotebookLM intake queue
- What funding research arrived?
- What marketing research is pending?

## Results
- NotebookLM prompts routed internal-first (`topic=notebooklm`) with confidence label.
- Funding prompt routed internal-first (`topic=funding`).
- Marketing prompt routed internal-first (`topic=marketing`) after keyword expansion.
- Telegram response format remained concise and non-spammy.

## Confidence + Formatting
- Confidence labels present (`INTERNAL_CONFIRMED` / `INTERNAL_PARTIAL` based on data availability).
- Output remained short and actionable.
