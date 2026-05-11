# Live Beta Invite Flow Test

Date: 2026-05-10

Status: partially verified from shell; full live acceptance still requires external tester inbox/device interaction.

Verified here:
- Invite endpoint exists and is callable path-wise.
- Waive-payment and tester-tagging paths are present.
- Beta invite email v2 copy prepared.

Not fully verifiable in shell-only context:
- actual inbox receipt/open/click behavior
- end-user signup and dashboard session from invited account
- mobile login friction on live tester device

Recommended next live check:
1. Send invite to disposable tester inbox.
2. Confirm click-through and sign-up.
3. Validate waived billing and dashboard access.
4. Run one Hermes prompt from mobile session.
