# Nexus Browser Worker Registry
# Pattern: supervised Playwright tasks for low-risk page editing

## How to Use

1. Quit any conflicting browser (Chrome must be closed if script uses Chrome profile)
2. Run: `python3 scripts/browser_tasks/<script_name>.py`
3. Browser opens in headed (visible) mode — watch and intervene if needed
4. Press ENTER at prompts to advance
5. Review screenshots in `artifacts/browser_tasks/<site>/`
6. Manually approve any publish/billing actions — scripts NEVER do this automatically

---

## Registered Workers

| Task | Script | Target | Safety | Approval Req | Screenshots |
|------|--------|--------|--------|-------------|-------------|
| beehiiv_setup_assist | scripts/browser_tasks/beehiiv_setup_assist.py | app.beehiiv.com | LOW_RISK | Publish: YES | artifacts/browser_tasks/beehiiv/ |

---

## Worker Template

```python
WORKER_METADATA = {
    "task_name":         "your_task_name",
    "target_site":       "https://example.com",
    "safety_level":      "LOW_RISK | MEDIUM_RISK | HIGH_RISK",
    "required_approval": {
        "publish":    True,
        "billing":    "BLOCKED",
        "send_email": "BLOCKED",
    },
    "screenshots_path":  "artifacts/browser_tasks/<site>/",
    "mode":              "headed (supervised)",
    "final_status":      "completed | needs_manual | blocked",
}
```

## Safety Levels

| Level | Meaning | Auto-allowed |
|-------|---------|-------------|
| LOW_RISK | Text/content editing, reading pages | Yes |
| MEDIUM_RISK | Form submission, file upload, settings | Require confirmation prompt |
| HIGH_RISK | Publish, billing, send email, delete | BLOCKED — manual only |

## Absolute Blocks (All Workers)

These actions are blocked in all browser workers regardless of safety level:
- Clicking "Publish", "Send Now", "Launch", "Go Live"
- Clicking "Upgrade", "Subscribe to Plan", "Billing", "Payment"
- Clicking "Send Broadcast", "Confirm Send"
- Storing, logging, or printing credentials
- Auto-purchasing anything

## Chrome Profile Note

Scripts that use the existing Chrome profile (`CHROME_USER_DATA`) can reuse
authenticated sessions without requiring credentials. Chrome must be **closed**
before the script runs — only one process can hold the profile lock.

## Artifacts Structure

```
artifacts/
  browser_tasks/
    beehiiv/
      HHMMSS_01_beehiiv_landing.png
      HHMMSS_02_dashboard.png
      ...
    [other_sites]/
      ...
```
