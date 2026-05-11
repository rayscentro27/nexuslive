# Beta Invite Email Upgrade

Date: 2026-05-10

## Upgrades Applied
- Subject changed to: `You’ve Been Invited to Join Nexus Beta`.
- Expanded onboarding guidance and expectations.
- Added mobile/PWA access section.
- Added waived beta-access language.
- Added comprehensive compliance disclaimer block.
- Added support/help close and website reference.

## Validation
- Template tests passed (`scripts/test_beta_invite_email_template.py`).
- Email report safety tests passed.

## Sample (Redacted)
- Subject: You’ve Been Invited to Join Nexus Beta
- Signup link: `https://.../signup?token=...` (redacted)

## Non-breaking Behavior
- Invite endpoint path unchanged.
- Waiver logic unchanged.
