# Q-Net 010 behavior workflow completion handoff

## Repository

- Branch: `feature/qnet-010-behavior-validation`
- Base: `fc3c8a77a80c1770a674feecb338a2abf09965a3`
- Completion commit: see final report; no amend, rebase, push or tag

## Implemented

- Added generic scenario metadata to public operation requirements without special-casing problem state in the engine.
- Aggregated detailed actual-wiring checks into PB1, PB2, STOP, EOCR and power-off/restore scenarios.
- Each UI card exposes only public status, observation count, missing behavior labels and the next user action.
- Added `unavailable` when static safety inspection prevents power; incomplete/bypassed wiring remains `unsatisfied`.
- Added top-level public expectation paths so power state itself can be validated.
- Strengthened STOP, EOCR and power tests to require timer stopped/0ms and prior motor operation.
- Verified the private corrected candidate through SQLite save, duplicate save, application restart, operation-session creation and five scenarios.
- Removed fuse terminal evidence from readiness blocking; Q-Net 010 remains draft/unverified because this is ungraded practice, not an official answer.

## Storage and privacy

- Practice drafts remain isolated by user, problem and workspace.
- The candidate is never auto-applied to normal users; browser verification seeded only an isolated temporary workspace.
- Public problem detail and result APIs do not return expected Nets, alternatives, private operation tests, candidate classification/path or private Net IDs.
- `docs/private` and private audit/test material remain excluded by the distribution packer.
- Existing SQLite, user profiles, free circuits and wiring records require no migration and were not touched.

## User workflow

```text
Q-Net 010 → circuit analysis autosave → wiring autosave
→ operation session from latest saved snapshot
→ manual power/PB/LS/EOCR/fuse actions
→ five behavior cards
→ return to wiring → edit → new operation session
```

## Remaining work

- No score, answer comparison or pass/fail is planned for this workflow.
- The private candidate remains development evidence rather than an official answer.
- Q-Net 001-009 and 011-018 remain separate future problem implementations.
- Future shared-engine changes should continue with focused tests followed by the complete suite.

## Verification commands

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_all.ps1
.venv\Scripts\python.exe scripts\validate_problems.py
.venv\Scripts\python.exe scripts\check_qnet_010_readiness.py
.venv\Scripts\python.exe scripts\run_qnet_18_smoke_test.py
Set-Location frontend
npm run typecheck
npm run build
```

See `TEST_RESULTS_QNET_010_BEHAVIOR_COMPLETION_2026-08-25.md` and `docs/qnet-010-manual-test-behavior-completion-2026-08-25.md` for exact results.
