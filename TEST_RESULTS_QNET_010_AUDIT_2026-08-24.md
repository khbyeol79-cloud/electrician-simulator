# Test Results - Q-Net 010 private functional validation

Date: 2026-08-24 (Asia/Seoul)

## Baseline

- Base: `ca87754f320be5c73d05bfb1dfaf6cc7cf5e3e7a`, tag `v0.13.0-stable-fuse`
- Preserved documentation commit: `7a65a59c2c76051b6e41157f2800671892b91546`
- Python: 3.14.6, rebuilt project `.venv`
- `pip check`: PASS

## Final automated results

| Check | Command | Result |
| --- | --- | --- |
| Full Python suite | `.venv\Scripts\python.exe -m pytest` | 185 passed, 1 deprecation warning |
| Q-Net 010 private suite | `.venv\Scripts\python.exe -m pytest backend/tests/test_qnet_010_private_validation.py -q` | 34 passed |
| Package validation | `.venv\Scripts\python.exe scripts\validate_problems.py` | 23 loaded, 0 errors, 19 intended unverified warnings |
| Frontend | `npm test` | 7 files, 67 passed |
| TypeScript | `npm run typecheck` | PASS |
| Production build | `npm run build` | PASS, 63 modules |
| Privacy regression | focused pytest command | 49 passed |
| Basic board demo | `scripts/run_basic_board_demo.py` | PASS |
| Empty board demo | `scripts/run_empty_board_demo.py` | PASS |
| Q-Net inventory smoke | `scripts/run_qnet_18_smoke_test.py` | PASS, 18/18 |
| Q-Net 010 smoke | same command with `--problem 010` | PASS, draft/unverified |
| Readiness | `scripts/check_qnet_010_readiness.py --allow-blocked` | 19 PASS / 1 evidence BLOCKED |

The single Python warning is Starlette TestClient/httpx deprecation and is not a test failure.

## Q-Net 010 coverage

The 34 dedicated tests cover:

- canonical wiring;
- missing and wrong terminals;
- direct and phase-to-phase shorts;
- separated-Net merges;
- STOP, FUSE, EOCR, timer, MC main-contact, MC auxiliary-contact, and forced-coil bypasses;
- isolated TB jumpers and reject policy;
- terminal capacity overflow;
- TB renumbering and alternate wire trees;
- whole X1/X2/T1/T2 changeover-group swaps;
- rejection of partial pin substitution;
- actual-wiring PB1/PB2 timer flows;
- STOP and EOCR behavior;
- power/reset state isolation;
- public grading and operation blocking;
- API, source, and production-bundle answer secrecy.

## Status decision

Internal functional validation is complete, but the official physical FUSE numbering is not. Q-Net 010 therefore remains `draft/unverified` and inaccessible for public grading and operation.
