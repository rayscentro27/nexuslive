# Mobile App Icon Audit

Date: 2026-05-10

## Findings
- This repo contains web/dashboard runtime assets and generated site outputs.
- A dedicated React Native/Expo app config was not confirmed in this pass.
- Brand-consistent icon/logo placeholders were added under `public/brand/`:
  - `nexus-logo.svg`
  - `nexus-mark.svg`
  - `app-icon.svg`
  - `hermes-avatar.svg`
  - `social-preview.svg`

## Safe Next Steps
- If PWA/web manifest exists elsewhere, wire `app-icon.svg` conversions to PNG sizes (192/512).
- If mobile branch is external/Claude-owned, share `brand/*_spec.md` + `public/brand/*` as source pack.
- Keep icon changes additive; do not break existing app routing or runtime bundles.
