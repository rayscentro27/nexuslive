# Nexus Repository Workflow Policy

## Source Of Truth

1. `main` is the source of truth unless Ray explicitly approves a temporary preview branch.
2. Preview branches are temporary. Completed work must be merged or cherry-picked to `main`, or abandoned with a written reason.
3. No implementation is complete if it exists only in a local checkout or temporary branch.

## Completion Requirements

Every completed source task must:

1. End with `git status --short`.
2. Commit safe source changes using exact paths.
3. Push `main` after verification unless Ray explicitly pauses the push.
4. Report the branch, commit SHA, push result, and remaining deployment action.
5. For UI work, report the route, navigation location, build result, push status, and deployment status.
6. Surface generated proof through Showroom, Operator Core, or a safe tracked manifest when Ray needs to verify it.

Generated runtime files alone are not sufficient proof. Ray must be able to reach or review the result through an approved interface or artifact.

## Verification Standard

Work is not complete when:

- Ray cannot verify the result.
- The route exists but is not linked from the expected navigation.
- The source is committed but not pushed.
- The push succeeded but the deployment state is unknown.
- A generated report exists only in ignored local storage and is not surfaced safely.

## Repository Safety

- Never commit `.env` files, token backups, credentials, private keys, raw receipts, logs, runtime outputs, or private customer data.
- Never use `git add .` or `git add -A`.
- Stage exact reviewed paths only.
- Run a targeted secret scan on files included in commits before pushing.
- Do not force-push `main`.
- Do not discard unrelated user or runtime changes.
- Do not run broad ignored-file status scans.

## Branch And Deployment Discipline

- Use a preview branch only when isolation is explicitly required.
- Once preview work is accepted and verified, move it to `main` promptly.
- A push and a deployment are separate facts; report both.
- Do not claim a UI is live until the deployment serving the target domain contains the expected commit.
- Manual production deployment requires Ray's explicit approval when automatic deployment is unavailable.
