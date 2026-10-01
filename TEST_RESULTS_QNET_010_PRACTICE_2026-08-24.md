# Q-Net 010 ungraded practice mode - test results

Date: 2026-08-24

Base: `c60d2745cdd3858a46dda16359e63923808430a9`
Branch: `feature/qnet-010-practice-mode`

## Baseline before feature changes

- `scripts/test_all.ps1`: Python 193 PASS; validator 23 loaded/0 errors/19 intended warnings; frontend 68 PASS; Vite 64 modules PASS.
- `npm run typecheck`: PASS.
- Q-Net 010 focused/private candidate tests: 42 PASS using a controlled Windows temporary directory.
- Readiness: 19 PASS / 1 BLOCKED.

## Final automated results

| Command | Result |
| --- | --- |
| `$env:TEMP=...; $env:TMP=...; powershell -File scripts/test_all.ps1` | Python 196 PASS, 2 warnings; validator 23/0 errors/19 warnings; frontend 69 PASS; Vite 64 modules PASS |
| `npm run typecheck` | PASS |
| `npm test -- --run` | 7 files, 69 PASS |
| `npm run build` | PASS, 64 modules |
| `.venv\Scripts\python.exe scripts\check_qnet_010_readiness.py --allow-blocked` | 19 PASS / 1 BLOCKED |
| `.venv\Scripts\python.exe scripts\run_basic_board_demo.py` | PASS |
| `.venv\Scripts\python.exe scripts\run_empty_board_demo.py` | PASS |
| `.venv\Scripts\python.exe scripts\run_qnet_18_smoke_test.py` | PASS, all 18 |
| `.venv\Scripts\python.exe scripts\run_qnet_18_smoke_test.py --problem 010` | PASS |
| `rg` private marker scan over `frontend/src` and `frontend/dist` | no private answer markers |

The first final `scripts/test_all.ps1` attempt reached 112 tests but produced 82 setup errors because the default Windows pytest temporary folder denied access. This was an environment error, not a code failure. The unchanged script passed after assigning a project-external controlled TEMP/TMP. The remaining two warnings are the existing Starlette deprecation warning and a non-fatal pytest cache permission warning.

## Coverage added or changed

- Explicit Q-Net 010 capability matrix and other 17 official-draft blocks.
- Direct grading API bypass denial.
- Separate draft metadata, workspace/user isolation, database schema migration, and file-handle compatibility.
- Practice session without accepted answer snapshot; a test replaces the private answer object with an exception-throwing sentinel and still creates/powers the session.
- Practice state contains no score, pass, correctness, expected-Net, or automatic-check result.
- Phase/return short and dual-FUSE channel merge block power.
- Unknown, duplicate, and capacity-invalid connections continue to be rejected by public structural validation.
- Legacy two-terminal and new four-terminal FUSE palette availability.
- Frontend persistent practice banner and absence of a grading submit button.
- Wrong-wire routing remains visible instead of crashing.

## Non-exposure

General problem responses, practice drafts/sessions, error bodies, HTML, source, and generated bundle were checked for private Q-Net answer markers. Practice endpoints depend on manifest capabilities, public circuit/operation definitions, the user draft, and the device catalog; they do not execute answer comparison or `operation_tests`.
