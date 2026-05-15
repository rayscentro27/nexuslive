#!/usr/bin/env python3
"""Send CEO final night demo-ready summary email."""
import sys
sys.path.insert(0, '/Users/raymonddavis/nexus-ai')

from notifications.operator_notifications import send_operator_email

SUBJECT = "Nexus Final Night Demo-Ready Pass — COMPLETE"

PLAIN = """NEXUS FINAL NIGHT DEMO-READY SUMMARY
Date: 2026-05-13
Commit: nexuslive main b98c2d2 | nexus-ai agent-coord-clean 435ceb5

STATUS: DEMO-READY

PHASES COMPLETED
A  Demo automation visibility      LIVE
B  Animated workforce immersion    UPGRADED (Live Ops 4th panel)
C  Mobile wow factor               IMPROVED
D  Browser QA automation           9/9 PASSED
E  Hermes conversational quality   4/5 INTERCEPTED
F  CEO email presentation          CONFIGURED
G  Invite email + tester flow      READY TO SEND
H  Spam / noise cleanup            COMPLETE
I  Playlist ingestion readiness    READY (gated)
J  Final tests                     ALL PASS
K  Git push + DB push              DONE

SAFETY
NEXUS_DRY_RUN=true              OK
LIVE_TRADING=false              OK
TRADING_LIVE_EXECUTION_ENABLED=false  OK
NEXUS_AUTO_TRADING=false        OK
No secrets exposed              OK
No live trading                 OK

REMAINING MANUAL ACTIONS
1. Send tester invite to rayscentro@yahoo.com
2. Set SCHEDULER_EMAIL_ENABLED=true + Gmail app password
3. Run playlist_ingest_worker with PLAYLIST_INGEST_WRITES_ENABLED=true
4. Approve more knowledge as transcripts process
5. Verify Resend domain once Cloudflare block clears (~24h)
6. Add rayscentro@yahoo.com to Hermes approved list after signup
"""

HTML = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:32px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

<tr><td style="background:linear-gradient(135deg,#1a1c3a,#3d5af1);border-radius:12px 12px 0 0;padding:32px 36px;">
  <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:-0.3px">Nexus Final Night Demo-Ready Pass</h1>
  <p style="margin:8px 0 0;color:#a5b4fc;font-size:13px">2026-05-13 &nbsp;|&nbsp; nexuslive: b98c2d2 &nbsp;|&nbsp; nexus-ai: 435ceb5</p>
</td></tr>

<tr><td style="background:#1a1c2e;padding:28px 36px;">
  <div style="background:#14532d22;border-left:4px solid #16a34a;border-radius:6px;padding:14px 18px;margin-bottom:20px;">
    <p style="margin:0;color:#86efac;font-size:15px;font-weight:700">STATUS: DEMO-READY &nbsp;&#10003;</p>
    <p style="margin:6px 0 0;color:#d1fae5;font-size:13px">All 10 phases complete. 9/9 QA tests passing. Vite build clean. Git pushed.</p>
  </div>

  <h3 style="color:#a5b4fc;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px">Phases Completed</h3>
  <table width="100%" cellpadding="6" cellspacing="0" style="font-size:13px;color:#e2e8f0;border-collapse:collapse;">
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">A</td><td>Demo automation visibility</td><td style="color:#4ade80;text-align:right">LIVE</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">B</td><td>Animated workforce immersion</td><td style="color:#4ade80;text-align:right">UPGRADED</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">C</td><td>Mobile wow factor</td><td style="color:#4ade80;text-align:right">IMPROVED</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">D</td><td>Browser QA automation</td><td style="color:#4ade80;text-align:right">9/9 PASSED</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">E</td><td>Hermes conversational quality</td><td style="color:#4ade80;text-align:right">4/5 INTERCEPTED</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">F</td><td>CEO email presentation</td><td style="color:#4ade80;text-align:right">CONFIGURED</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">G</td><td>Invite email + tester flow</td><td style="color:#fbbf24;text-align:right">READY TO SEND</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">H</td><td>Spam / noise cleanup</td><td style="color:#4ade80;text-align:right">COMPLETE</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">I</td><td>Playlist ingestion readiness</td><td style="color:#4ade80;text-align:right">READY (gated)</td></tr>
    <tr style="border-bottom:1px solid #2d3748"><td style="color:#94a3b8">J</td><td>Final tests</td><td style="color:#4ade80;text-align:right">ALL PASS</td></tr>
    <tr><td style="color:#94a3b8">K</td><td>Git push + DB push</td><td style="color:#4ade80;text-align:right">DONE</td></tr>
  </table>

  <h3 style="color:#a5b4fc;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin:24px 0 12px">Safety Verification</h3>
  <div style="background:#0f172a;border-radius:8px;padding:14px 18px;">
    <table width="100%" cellpadding="4" cellspacing="0" style="font-size:12px;font-family:monospace;">
      <tr><td style="color:#94a3b8">NEXUS_DRY_RUN=true</td><td style="color:#4ade80;text-align:right">OK</td></tr>
      <tr><td style="color:#94a3b8">LIVE_TRADING=false</td><td style="color:#4ade80;text-align:right">OK</td></tr>
      <tr><td style="color:#94a3b8">TRADING_LIVE_EXECUTION_ENABLED=false</td><td style="color:#4ade80;text-align:right">OK</td></tr>
      <tr><td style="color:#94a3b8">NEXUS_AUTO_TRADING=false</td><td style="color:#4ade80;text-align:right">OK</td></tr>
      <tr><td style="color:#94a3b8">No secrets in code</td><td style="color:#4ade80;text-align:right">OK</td></tr>
      <tr><td style="color:#94a3b8">No live trading</td><td style="color:#4ade80;text-align:right">OK</td></tr>
    </table>
  </div>

  <h3 style="color:#fbbf24;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin:24px 0 12px">Remaining Manual Actions</h3>
  <div style="background:#1c1410;border-left:4px solid #f59e0b;border-radius:6px;padding:14px 18px;">
    <ol style="margin:0;padding-left:18px;color:#fef3c7;font-size:13px;line-height:1.8;">
      <li>Send tester invite to rayscentro@yahoo.com</li>
      <li>Set SCHEDULER_EMAIL_ENABLED=true + Gmail app password</li>
      <li>Run playlist_ingest_worker with PLAYLIST_INGEST_WRITES_ENABLED=true</li>
      <li>Approve more knowledge as transcripts process (target: 5-10)</li>
      <li>Verify Resend domain once Cloudflare block clears (~24h)</li>
      <li>Add rayscentro@yahoo.com to Hermes approved list after signup</li>
    </ol>
  </div>
</td></tr>

<tr><td style="background:#13152a;border-radius:0 0 12px 12px;padding:16px 36px;text-align:center;">
  <p style="margin:0;color:#4b5563;font-size:11px">Nexus AI &nbsp;|&nbsp; goclearonline.cc &nbsp;|&nbsp; Auto-generated by Nexus CEO Worker</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

ok, detail = send_operator_email(SUBJECT, PLAIN, HTML)
print(f"CEO email: {'SENT' if ok else 'FAILED'} — {detail}")
