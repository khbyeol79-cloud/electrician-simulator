# Handoff - Q-Net 010 ungraded practice mode

## State

- Branch: `feature/qnet-010-practice-mode`
- Base commit: `c60d2745cdd3858a46dda16359e63923808430a9`
- Product version remains 0.13.0; document suffix dev5 identifies this development handoff only.
- Q-Net 010 remains `status=draft`, answer `verification=unverified`, `wiring_gradable=false`, `operation_gradable=false`.

## Architecture

Manifest capabilities are resolved centrally by `ProblemRepository`. Only Q-Net 010 declares board/edit/preview access while grading is disabled. Other official drafts inherit the previous fully blocked policy.

Practice wiring is stored in SQLite schema 10 table `practice_wiring_drafts`, keyed by problem and workspace inside the existing per-user database pool. It never overwrites `wiring_drafts`, accepted attempts, free-circuit workspaces, or existing user records. Rows identify `user_practice_draft`, unverified, ungradable data.

`practice_preview_session` takes a fixed copy of that user draft. It reuses the catalog composer and `OperationEngine`; it does not obtain an accepted wiring attempt, compare expected Nets/alternatives, run answer operation tests, or save grading progress. `verified_operation_session` retains the established accepted-snapshot and run-check path. `free_circuit_session` is also identified explicitly.

Answer-independent safety validation rejects malformed terminals/duplicates/capacity through `WiringService`, blocks source/return or phase shorts and cross-channel dual-FUSE merges, and emits structural bypass warnings. Blocking issues disable power but do not produce correct/incorrect/pass/fail results.

## FUSE compatibility

Q-Net 010 uses existing `fuse_dual_4terminal_training`: one body, two cartridges, external F-1 to F-4, intrinsic independent pairs 1-2 and 3-4. The existing `fuse_single_pole_training` ID and behavior remain unchanged. Free circuit keeps palette ID `fuse` and adds separate `dual_fuse`; stored devices are not migrated.

## Evidence and security

PDF pages 6-9 and SHA-256 were rechecked. Structure is supported; official numeric terminal evidence is not. Readiness stays 19 PASS / 1 BLOCKED. Public API/bundle tests keep expected Nets, alternatives, operation tests, canonical answers, and the user candidate audit private. Practice session creation is tested with private answer access made impossible.

## Validation and next order

- Final: Python 196, frontend 69, packages 23/0 errors, TypeScript/build PASS, basic/empty/Q-Net 18 smoke PASS.
- Manual limitations are listed in `qnet-010-practice-manual-test-0.14.0-dev5.md`.
- Next: manually load a complete safe Q-Net 010 user draft; exercise the full PB/LS/timer/MC/lamp/motor/EOCR sequence; collect manufacturer or official numbered FUSE evidence; only then consider verified grading. Circuit-analysis socket questions remain a separate future scope.
