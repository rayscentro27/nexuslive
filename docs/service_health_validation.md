# Service Health Validation Checklist

Use after every optional service stop/start test.

## Mandatory Checks
- [ ] Telegram replies succeed for a safe operational query
- [ ] Workforce Operations Center loads for authenticated admin
- [ ] Admin auth blocks unauthenticated access (`403` expected)
- [ ] Invite flow endpoints/templates remain healthy
- [ ] CEO report path remains available
- [ ] Knowledge review path remains available
- [ ] Email reporting path still sends or reports configured status correctly
- [ ] Remote access path (SSH or chosen tunnel) remains stable

## Validation Commands / Actions
- Telegram: send one operator status query and confirm reply
- Admin auth/workforce: verify `/admin/workforce-operations` with and without auth token
- Email path: run `python3 scripts/test_email_reports.py`
- Parser path: run `python3 scripts/test_knowledge_email_intake_parser.py`

## Failure Policy
If any check fails:
1. Roll back the last service change immediately
2. Re-run full mandatory checks
3. Mark service as not safe to pause
